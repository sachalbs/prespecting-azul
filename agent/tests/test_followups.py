"""Relances: delay-gated, capped, human-approved, cancelled the moment they reply.

Reply rate counts unique prospects (never emails) once follow-ups multiply touches.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, ClassVar

import pytest

from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.db.models import Message
from azul.db.session import session_scope
from azul.enums import MessageStatus
from azul.memory import EpisodicMemory
from azul.orchestrator import campaign as camp
from azul.writing.linter import lint

CSV = "email,full_name,company,segment\n" + "\n".join(
    f"p{i}@acme.com,Person {i},Acme,saas" for i in range(1, 3)
)


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _campaign_sent(tmp_path: Path, *, days_ago: float) -> uuid.UUID:
    """A 2-prospect campaign whose step-1 touches were SENT `days_ago` days ago."""
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))
    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
        camp.approve(s, campaign_id=cid, approve_all=True)
    _mark_step_sent(cid, step=1, days_ago=days_ago)
    return cid


def _mark_step_sent(cid: uuid.UUID, *, step: int, days_ago: float) -> None:
    with session_scope() as s:
        msgs = s.query(Message).filter(Message.campaign_id == cid, Message.step == step).all()
        for m in msgs:
            m.status = MessageStatus.SENT
            m.sent_at = _now() - timedelta(days=days_ago)
            m.external_id = m.external_id or f"ext-{m.id}"


def _followup_drafts(cid: uuid.UUID) -> list[tuple[int, str]]:
    with session_scope() as s:
        return [
            (m.step, str(m.prospect_id))
            for m in s.query(Message)
            .filter(Message.campaign_id == cid, Message.step > 1)
            .order_by(Message.step)
        ]


class RecordingChannel(Channel):
    name: ClassVar[str] = "recording"

    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, message: OutboundMessage) -> SendResult:
        assert message.to_email is not None
        self.sent.append(message.to_email)
        return SendResult(external_id=f"ext-{message.to_email}")

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        return []


# ── delay ────────────────────────────────────────────────────────────────────


def test_no_followup_before_the_delay(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=2)
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4) == 0
    assert _followup_drafts(cid) == []


def test_followup_drafted_after_the_delay_as_child_draft(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=5)
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4) == 2
        # Idempotent: a second run never duplicates the relance.
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4) == 0
    with session_scope() as s:
        relances = s.query(Message).filter(Message.campaign_id == cid, Message.step == 2).all()
        assert len(relances) == 2
        for r in relances:
            assert r.status == MessageStatus.DRAFT  # human gate: never auto-sent
            assert r.parent_message_id is not None  # a distinct touch, linked (flywheel)
            parent = next(
                m for m in s.query(Message).filter(Message.campaign_id == cid, Message.step == 1)
                if m.id == r.parent_message_id
            )
            assert parent.prospect_id == r.prospect_id
            if parent.subject:
                assert r.subject == f"Re: {parent.subject}"


# ── cap ──────────────────────────────────────────────────────────────────────


def test_followup_cap_is_respected(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=10)
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4, max_followups=2) == 2
    _mark_step_sent(cid, step=2, days_ago=6)
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4, max_followups=2) == 2
    _mark_step_sent(cid, step=3, days_ago=5)
    with session_scope() as s:  # cap reached: silence, but no step 4 — ever
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4, max_followups=2) == 0
    assert all(step <= 3 for step, _ in _followup_drafts(cid))


# ── cancel on reply ──────────────────────────────────────────────────────────


def test_replied_prospect_gets_no_followup(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=5)
    with session_scope() as s:
        EpisodicMemory(s).ingest_reply(
            InboundReply(text="Interested!", from_email="p1@acme.com")
        )
    with session_scope() as s:
        assert camp.generate_followups(s, campaign_id=cid, delay_days=4) == 1  # only p2
    assert len(_followup_drafts(cid)) == 1


def test_reply_cancels_pending_followups_immediately(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=5)
    with session_scope() as s:
        camp.generate_followups(s, campaign_id=cid, delay_days=4)
        camp.approve(s, campaign_id=cid, approve_all=True)  # relances approved, not sent
    with session_scope() as s:  # the reply lands BEFORE the relance goes out
        EpisodicMemory(s).ingest_reply(
            InboundReply(text="Got your note", from_email="p1@acme.com")
        )
    with session_scope() as s:
        p1_relance = (
            s.query(Message)
            .filter(Message.campaign_id == cid, Message.step == 2)
            .join(Message.prospect)
            .filter(Message.prospect.has(email="p1@acme.com"))
            .one()
        )
        assert p1_relance.status == MessageStatus.SKIPPED


def test_send_approved_skips_followup_when_reply_arrived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _campaign_sent(tmp_path, days_ago=5)
    with session_scope() as s:
        camp.generate_followups(s, campaign_id=cid, delay_days=4)
        camp.approve(s, campaign_id=cid, approve_all=True)
        # Reply recorded straight on the outcome (bypasses ingest's own cancel)
        # to prove the send-time guard holds on its own.
        p1_step1 = (
            s.query(Message)
            .filter(Message.campaign_id == cid, Message.step == 1)
            .filter(Message.prospect.has(email="p1@acme.com"))
            .one()
        )
        EpisodicMemory(s).record_outcome(message_id=p1_step1.id, replied=True)
    ch = RecordingChannel()
    monkeypatch.setattr(camp, "get_channel", lambda: ch)
    with session_scope() as s:
        assert camp.send_approved(s, campaign_id=cid) == 1  # only p2's relance leaves
    assert ch.sent == ["p2@acme.com"]
    with session_scope() as s:
        p1_relance = (
            s.query(Message)
            .filter(Message.campaign_id == cid, Message.step == 2)
            .filter(Message.prospect.has(email="p1@acme.com"))
            .one()
        )
        assert p1_relance.status == MessageStatus.SKIPPED


# ── reply rate on unique prospects ───────────────────────────────────────────


def test_reply_rate_counts_unique_prospects_not_emails(tmp_path: Path) -> None:
    cid = _campaign_sent(tmp_path, days_ago=5)
    with session_scope() as s:
        camp.generate_followups(s, campaign_id=cid, delay_days=4)
        camp.approve(s, campaign_id=cid, approve_all=True)
    _mark_step_sent(cid, step=2, days_ago=0)  # 2 prospects x 2 touches = 4 emails
    with session_scope() as s:
        mem = EpisodicMemory(s)
        for m in (
            s.query(Message)
            .filter(Message.campaign_id == cid)
            .filter(Message.prospect.has(email="p1@acme.com"))
        ):  # p1 answers BOTH emails: still one replying prospect
            mem.record_outcome(message_id=m.id, replied=True)
    with session_scope() as s:
        r = camp.build_report(s, campaign_id=cid)
    assert r.sent == 4  # emails (touches)
    assert r.contacted == 2  # unique prospects — the denominator
    assert r.replied == 1  # p1 counts ONCE despite two reply outcomes
    assert r.reply_rate == pytest.approx(0.5)


# ── playbook holds for relances ──────────────────────────────────────────────


def test_linter_rejects_lazy_followup_phrases() -> None:
    assert any("je relance" in v for v in lint("Bonjour, je relance suite à mon message."))
    assert any("petit up" in v for v in lint("Un petit up au cas où."))
    assert any(
        "je n'ai pas eu de retour" in v
        for v in lint("Je n'ai pas eu de retour de votre part.")
    )
