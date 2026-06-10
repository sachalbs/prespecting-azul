"""`redraft` regenerates a campaign's drafts in place — no resolver/finder/research."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import ClassVar

import pytest
from sqlalchemy import select

from azul.db.models import Message, Research
from azul.db.session import session_scope
from azul.enums import MessageStatus, ReviewDecision
from azul.orchestrator import campaign as camp
from azul.orchestrator.graph import build_pipeline
from azul.writing.base import Draft, DraftRequest, Writer

CSV = "email,full_name,company,segment\nann@acme.fr,Ann Roy,Acme,saas\n"


class _TaggedWriter(Writer):
    """Emits a body tagged with a version + echoes the hook/language it received."""

    name: ClassVar[str] = "tagged"

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.seen: list[DraftRequest] = []

    def write(self, request: DraftRequest) -> Draft:
        self.seen.append(request)
        return Draft(
            body=f"[{self.tag}] hook={request.hook} lang={request.target_language}",
            subject=f"{self.tag} subject",
            angle="redraft",
        )


def _campaign_with_draft(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, writer: Writer, csv: str = CSV
) -> uuid.UUID:
    p = tmp_path / "p.csv"
    p.write_text(csv, encoding="utf-8")
    pipeline = build_pipeline(writer=writer)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)
    with session_scope() as s:
        return camp.run_campaign(
            s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p))
        ).id


def test_redraft_replaces_body_reusing_hook_and_language(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _campaign_with_draft(tmp_path, monkeypatch, _TaggedWriter("v1"))
    with session_scope() as s:
        m = s.scalars(select(Message)).one()
        m.prospect.target_language = "fr"  # a persisted language redraft must reuse
        assert "[v1]" in m.body

    redraft_writer = _TaggedWriter("v2")
    monkeypatch.setattr(camp, "get_writer", lambda: redraft_writer)
    with session_scope() as s:
        assert camp.redraft_campaign(s, campaign_id=cid) == 1

    with session_scope() as s:
        m = s.scalars(select(Message)).one()
        assert "[v2]" in m.body  # body regenerated
        assert "lang=fr" in m.body  # persisted language reused, not re-inferred
        assert m.status == MessageStatus.DRAFT
    assert redraft_writer.seen[0].hook is not None  # reused the stored research hook


def test_redraft_does_not_research_again(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _campaign_with_draft(tmp_path, monkeypatch, _TaggedWriter("v1"))
    with session_scope() as s:
        research_before = len(s.scalars(select(Research)).all())

    monkeypatch.setattr(camp, "get_writer", lambda: _TaggedWriter("v2"))
    with session_scope() as s:
        camp.redraft_campaign(s, campaign_id=cid)
    with session_scope() as s:
        assert len(s.scalars(select(Research)).all()) == research_before  # no new research


def test_redraft_skips_approved_and_human_edited(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    csv = "email,full_name,company\nann@acme.fr,Ann Roy,Acme\nbob@beta.fr,Bob Stone,Beta\n"
    cid = _campaign_with_draft(tmp_path, monkeypatch, _TaggedWriter("v1"), csv=csv)
    with session_scope() as s:
        msgs = s.scalars(select(Message).order_by(Message.created_at)).all()
        msgs[0].status = MessageStatus.APPROVED  # validated by the human
        msgs[1].human_edited_body = "ma version à moi"  # edited by the human
        msgs[1].review_decision = ReviewDecision.EDIT

    monkeypatch.setattr(camp, "get_writer", lambda: _TaggedWriter("v2"))
    with session_scope() as s:
        assert camp.redraft_campaign(s, campaign_id=cid) == 0  # nothing eligible

    with session_scope() as s:
        msgs = s.scalars(select(Message).order_by(Message.created_at)).all()
        assert "[v1]" in msgs[0].body  # approved one untouched
        assert msgs[1].human_edited_body == "ma version à moi"  # edit preserved


def test_redraft_no_drafts_returns_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _campaign_with_draft(tmp_path, monkeypatch, _TaggedWriter("v1"))
    with session_scope() as s:
        s.scalars(select(Message)).one().status = MessageStatus.SENT
    monkeypatch.setattr(camp, "get_writer", lambda: _TaggedWriter("v2"))
    with session_scope() as s:
        assert camp.redraft_campaign(s, campaign_id=cid) == 0
