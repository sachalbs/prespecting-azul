"""Discovery flow: ICP brief -> leads -> (approve list) -> drafts (stub, offline)."""

from __future__ import annotations

from azul.cli.chat import ChatSession
from azul.db.session import session_scope
from azul.orchestrator import campaign as camp


def test_discover_then_approve_list_creates_drafts() -> None:
    with session_scope() as s:
        campaign = camp.discover_campaign(
            s, tenant_slug="t1", name="agences growth FR",
            icp_brief="fondateurs d'agences growth FR, 5-30 personnes",
        )
        cid = campaign.id
        assert len(camp.list_leads(s, cid)) == 5
    with session_scope() as s:
        assert camp.approve_list(s, campaign_id=cid) >= 1
    with session_scope() as s:
        assert len(camp.list_drafts(s, cid)) >= 1


def test_chat_discovery_flow() -> None:
    cs = ChatSession()
    assert "leads" in cs.handle("discover fondateurs d'agences growth FR").lower()
    assert "[1]" in cs.handle("list")
    assert "brouillon" in cs.handle("approve-list").lower()
    assert "[1]" in cs.handle("show")
