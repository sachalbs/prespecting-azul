"""API cost tracker: per-call rows, price math, attribution, campaign aggregation."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from azul import costs
from azul.db.models import ApiCall, Campaign, Tenant
from azul.db.session import session_scope
from azul.orchestrator import campaign as camp

CSV = (
    "email,full_name,company,segment\n"
    "p1@acme.com,Person 1,Acme,saas\n"
    "p2@acme.com,Person 2,Acme,saas\n"
)


def _campaign(tmp_path: Path) -> uuid.UUID:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))
    with session_scope() as s:
        return camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id


def _bare_campaign() -> uuid.UUID:
    with session_scope() as s:
        t = Tenant(slug="t-cost", name="t-cost")
        s.add(t)
        s.flush()
        c = Campaign(tenant_id=t.id, name="bare")
        s.add(c)
        s.flush()
        return c.id


def test_llm_cost_math_from_usage_block() -> None:
    cid = _bare_campaign()
    with session_scope() as s:
        with costs.cost_context(campaign_id=cid, prospect_label="p1@acme.com"):
            costs.record_llm_usage(
                "deepseek",
                "draft",
                {"prompt_tokens": 1_000_000, "completion_tokens": 500_000},
            )
        s.flush()
        row = s.query(ApiCall).one()
        # DeepSeek defaults: $0.14/M in + $0.28/M out -> 0.14 + 0.14
        assert row.cost_usd == pytest.approx(0.28)
        assert (row.tokens_in, row.tokens_out) == (1_000_000, 500_000)
        assert row.campaign_id == cid
        assert row.prospect_label == "p1@acme.com"
        assert row.service == "deepseek"


def test_tavily_priced_per_call() -> None:
    cid = _bare_campaign()
    with session_scope() as s:
        with costs.cost_context(campaign_id=cid, prospect_label="p1@acme.com"):
            costs.record_call("tavily", "search")
            costs.record_call("tavily", "extract")
        s.flush()
        rows = s.query(ApiCall).all()
        assert len(rows) == 2
        assert all(r.cost_usd == pytest.approx(0.008) for r in rows)
        assert {r.operation for r in rows} == {"search", "extract"}


def test_record_without_open_session_still_persists() -> None:
    cid = _bare_campaign()
    with costs.cost_context(campaign_id=cid):
        costs.record_call("tavily", "search")  # no session_scope: fallback path
    with session_scope() as s:
        assert s.query(ApiCall).count() == 1


def test_missing_usage_block_records_zero_cost_not_a_crash() -> None:
    with session_scope() as s:
        costs.record_llm_usage("deepseek", "chat", None)
        s.flush()
        row = s.query(ApiCall).one()
        assert row.cost_usd == 0.0
        assert row.campaign_id is None  # unattributed: outside any cost context


def test_cost_summary_aggregates_by_service_and_per_prospect(tmp_path: Path) -> None:
    cid = _campaign(tmp_path)  # 2 prospects (stub run: no real API calls)
    with session_scope() as s:
        with costs.cost_context(campaign_id=cid, prospect_label="p1@acme.com"):
            costs.record_llm_usage(
                "deepseek", "draft", {"prompt_tokens": 500_000, "completion_tokens": 250_000}
            )  # 0.07 + 0.07 = 0.14
            costs.record_call("tavily", "search")  # 0.008
            costs.record_call("tavily", "extract")  # 0.008
        with costs.cost_context(campaign_id=cid, prospect_label="p2@acme.com"):
            costs.record_call("tavily", "search")  # 0.008
        # Noise from another campaign must not leak into this one's summary.
        with costs.cost_context(campaign_id=_other(s), prospect_label="x@y.z"):
            costs.record_call("tavily", "search")

    with session_scope() as s:
        summary = costs.build_cost_summary(s, campaign_id=cid)
    assert summary.total_usd == pytest.approx(0.14 + 3 * 0.008)
    by = {sc.service: sc for sc in summary.by_service}
    assert by["deepseek"].cost_usd == pytest.approx(0.14)
    assert by["deepseek"].tokens_in == 500_000
    assert by["tavily"].calls == 3
    assert by["tavily"].cost_usd == pytest.approx(0.024)
    assert summary.attributed_prospects == 2
    # Nothing sent yet -> denominator falls back to the campaign's memberships.
    assert summary.prospects_contacted == 2
    assert summary.cost_per_contacted_prospect == pytest.approx(summary.total_usd / 2)


def _other(s) -> uuid.UUID:  # noqa: ANN001 - test helper on an open session
    t = Tenant(slug=f"t-{uuid.uuid4().hex[:6]}", name="other")
    s.add(t)
    s.flush()
    c = Campaign(tenant_id=t.id, name="other")
    s.add(c)
    s.flush()
    return c.id
