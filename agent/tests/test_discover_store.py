"""Discovery store: scored table rendered, explicit selection promotes, rest stays."""

from __future__ import annotations

from sqlalchemy import select

from azul.db.models import Campaign, DiscoveryCandidate, Prospect
from azul.db.session import session_scope
from azul.discovery.base import ProspectCandidate
from azul.discovery.store import promote, ranked, render_table, save_candidates
from azul.enums import CampaignStatus
from azul.orchestrator.campaign import ensure_tenant


def _candidates(count: int) -> list[ProspectCandidate]:
    return [
        ProspectCandidate(
            company_name=f"Agence {i}",
            domain=f"agence{i}.fr",
            founder_name=f"Fondateur Num{i}",
            founder_role="CEO",
            source_url=f"https://annuaire.example/{i}",
            raw_context=f"Agence {i}, growth, Paris",
            icp_score=round(1.0 - i * 0.1, 2),
            score_reason=f"raison {i}",
        )
        for i in range(1, count + 1)
    ]


def test_table_renders_sorted_by_score_with_all_columns() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t1")
        rows = save_candidates(s, tenant.id, list(reversed(_candidates(3))))
        table = render_table(rows)
    lines = table.splitlines()
    assert "boîte" in lines[0] and "score" in lines[0] and "raison" in lines[0]
    assert "source" in lines[0] and "domaine" in lines[0] and "fondateur" in lines[0]
    # Sorted by score desc regardless of insertion order.
    body = lines[2:]
    assert "agence1.fr" in body[0] and "0.90" in body[0]
    assert "agence3.fr" in body[2]
    assert "raison 1" in body[0]


def test_selection_of_five_promotes_and_leaves_the_rest() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t1")
        rows = save_candidates(s, tenant.id, _candidates(8))
        chosen = ranked(rows)[:5]
        prospects, campaign = promote(s, tenant.id, chosen, campaign_name="discover test")
        tid = tenant.id
        cid = campaign.id
        assert len(prospects) == 5

    with session_scope() as s:
        prospects_db = s.scalars(select(Prospect).where(Prospect.tenant_id == tid)).all()
        assert len(prospects_db) == 5
        p = next(x for x in prospects_db if x.company_domain == "agence1.fr")
        # The existing Prospect format, ready for the pipeline.
        assert p.source == "discovery"
        assert p.full_name == "Fondateur Num1" and p.title == "CEO"
        assert p.email == "fondateur.num1@agence1.fr"  # best-guess placeholder, UNKNOWN status
        assert p.signals["icp_score"] == 0.9
        assert p.signals["source_url"] == "https://annuaire.example/1"

        all_rows = s.scalars(select(DiscoveryCandidate)).all()
        assert len(all_rows) == 8  # nothing deleted
        assert sum(1 for r in all_rows if r.promoted) == 5
        unpromoted = [r for r in all_rows if not r.promoted]
        assert all(r.prospect_id is None for r in unpromoted)

        campaign_db = s.get(Campaign, cid)
        assert campaign_db is not None
        assert campaign_db.status == CampaignStatus.DISCOVERED
        leads = list(campaign_db.leads)
        assert len(leads) == 5
        assert {ld["company_domain"] for ld in leads} == {
            f"agence{i}.fr" for i in range(1, 6)
        }


def test_promoted_campaign_feeds_the_existing_pipeline() -> None:
    from azul.orchestrator import campaign as camp

    with session_scope() as s:
        tenant = ensure_tenant(s, "t-pipe")
        rows = save_candidates(s, tenant.id, _candidates(2))
        _, campaign = promote(s, tenant.id, ranked(rows), campaign_name="discover pipe")
        cid = campaign.id
    with session_scope() as s:
        # The EXISTING approve_list entry point drafts from the promoted leads.
        assert camp.approve_list(s, campaign_id=cid) == 2
    with session_scope() as s:
        assert len(camp.list_drafts(s, cid)) == 2


def test_promote_without_founder_uses_contact_placeholder() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t2")
        rows = save_candidates(
            s,
            tenant.id,
            [ProspectCandidate(company_name="Sans Nom", domain="sansnom.fr")],
        )
        prospects, _ = promote(s, tenant.id, rows, campaign_name="x")
        assert prospects[0].email == "contact@sansnom.fr"
