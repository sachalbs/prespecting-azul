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


def _sent_campaign(tmp_path: Path) -> uuid.UUID:
    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company,segment\nann@acme.com,Ann Lee,Acme,saas\n", "utf-8")
    rows = camp.load_prospects_csv(str(p))
    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
    with session_scope() as s:
        camp.approve(s, campaign_id=cid, approve_all=True)
    with session_scope() as s:
        camp.send_approved(s, campaign_id=cid)
    return cid


def test_ingest_same_reply_twice_records_one_outcome(tmp_path: Path) -> None:
    from azul.connectors.base import InboundReply
    from azul.db.models import Outcome

    _sent_campaign(tmp_path)
    reply = InboundReply(
        text="sounds good",
        from_email="ann@acme.com",
        external_id="<r1@mail.example>",
        raw={"internetMessageId": "<r1@mail.example>", "subject": "Re: quick thought"},
    )
    with session_scope() as s:
        assert EpisodicMemory(s).ingest_reply(reply) is not None
    with session_scope() as s:
        assert EpisodicMemory(s).ingest_reply(reply) is None  # duplicate skipped
    with session_scope() as s:
        assert len(s.scalars(select(Outcome)).all()) == 1


def test_distinct_replies_both_recorded(tmp_path: Path) -> None:
    from azul.connectors.base import InboundReply
    from azul.db.models import Outcome

    _sent_campaign(tmp_path)
    r1 = InboundReply(
        text="first", from_email="ann@acme.com", external_id="<r1@x>",
        raw={"internetMessageId": "<r1@x>"},
    )
    r2 = InboundReply(
        text="second", from_email="ann@acme.com", external_id="<r2@x>",
        raw={"internetMessageId": "<r2@x>"},
    )
    with session_scope() as s:
        mem = EpisodicMemory(s)
        assert mem.ingest_reply(r1) is not None
    with session_scope() as s:
        assert EpisodicMemory(s).ingest_reply(r2) is not None
    with session_scope() as s:
        assert len(s.scalars(select(Outcome)).all()) == 2
