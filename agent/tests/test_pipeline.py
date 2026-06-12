"""End-to-end Jalon 0 pipeline on stub adapters: it runs and emits a number."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, select

from azul.db.models import Prospect
from azul.db.session import session_scope
from azul.orchestrator import campaign as camp

CSV = (
    "email,full_name,title,company,segment,recent_signal\n"
    "ann@acme.com,Ann Lee,VP Sales,Acme,saas,Raised a seed round\n"
    "bad-email,Bob Stone,Director,Ghostco,unknown,no valid email\n"
)


def _write_csv(tmp_path: Path) -> str:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    return str(p)


def test_csv_loads_two_rows(tmp_path: Path) -> None:
    rows = camp.load_prospects_csv(_write_csv(tmp_path))
    assert len(rows) == 2
    assert rows[0].signals.get("recent_signal") == "Raised a seed round"


def test_end_to_end_emits_reply_rate(tmp_path: Path) -> None:
    rows = camp.load_prospects_csv(_write_csv(tmp_path))

    with session_scope() as s:
        campaign = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows)
        cid = campaign.id

    with session_scope() as s:
        drafts = camp.list_drafts(s, cid)
        assert len(drafts) == 1  # invalid email never drafts
        assert camp.approve(s, campaign_id=cid, approve_all=True) == 1

    with session_scope() as s:
        assert camp.send_approved(s, campaign_id=cid) == 1

    with session_scope() as s:
        # idempotent: nothing approved remains, so no double-send
        assert camp.send_approved(s, campaign_id=cid) == 0

    with session_scope() as s:
        camp.simulate_replies(s, campaign_id=cid)
        report = camp.build_report(s, campaign_id=cid)
        assert report.sent == 1
        assert report.drafted == 1
        assert 0.0 <= report.reply_rate <= 1.0


def test_followups_drafted_for_non_repliers(tmp_path: Path) -> None:
    rows = camp.load_prospects_csv(_write_csv(tmp_path))
    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
    with session_scope() as s:
        camp.approve(s, campaign_id=cid, approve_all=True)
    with session_scope() as s:
        camp.send_approved(s, campaign_id=cid)
    with session_scope() as s:
        # delay_days=0: this test covers selection (sent + silent), not the delay
        # gate, which has its own tests in test_followups.py.
        assert camp.generate_followups(s, campaign_id=cid, delay_days=0) == 1
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=0) == 0  # idempotent


def test_rerun_upserts_prospects(tmp_path: Path) -> None:
    rows = camp.load_prospects_csv(_write_csv(tmp_path))
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows)
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q2", rows=rows)
    with session_scope() as s:
        count = s.scalar(select(func.count()).select_from(Prospect))
        assert count == 2  # same prospects, deduped on (tenant, email)
