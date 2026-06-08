"""Episodic relationship memory: Azul recalls prior touches with a person."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select

from azul.db.models import Prospect
from azul.db.session import session_scope
from azul.domain import ProspectBrief
from azul.memory import EpisodicMemory
from azul.orchestrator import campaign as camp
from azul.writing.base import DraftRequest
from azul.writing.prompts import build_messages

CSV = "full_name,company,company_domain,segment\nAnn Lee,Acme,acme.com,saas\n"


def test_recall_after_a_prior_send(tmp_path: Path) -> None:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))
    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
    with session_scope() as s:
        camp.approve(s, campaign_id=cid, approve_all=True)
    with session_scope() as s:
        camp.send_approved(s, campaign_id=cid)
    with session_scope() as s:
        prospect = s.scalars(select(Prospect)).first()
        assert prospect is not None
        note = EpisodicMemory(s).recall(prospect.id)
        assert note is not None
        assert "before" in note


def test_recall_none_for_unknown_prospect() -> None:
    with session_scope() as s:
        assert EpisodicMemory(s).recall(uuid.uuid4()) is None


def test_prompt_carries_relationship_note() -> None:
    msgs = build_messages(
        DraftRequest(
            prospect=ProspectBrief(email="a@b.com"),
            hook="h",
            relationship_note="reached this person 2x before",
        )
    )
    assert any("reached this person 2x before" in m["content"] for m in msgs)
