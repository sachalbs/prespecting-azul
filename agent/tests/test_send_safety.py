"""Send safety: per-send commits survive a mid-batch crash (no double-send)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

import pytest

from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.db.models import Message
from azul.db.session import session_scope
from azul.enums import MessageStatus
from azul.orchestrator import campaign as camp

CSV = "email,full_name,company,segment\n" + "\n".join(
    f"p{i}@acme.com,Person {i},Acme,saas" for i in range(1, 6)
)


class RecordingChannel(Channel):
    """Records every send; optionally crashes (hard, not ChannelError) at call N."""

    name: ClassVar[str] = "recording"

    def __init__(self, crash_at: int | None = None) -> None:
        self.sent: list[str] = []
        self.crash_at = crash_at

    def send(self, message: OutboundMessage) -> SendResult:
        if self.crash_at is not None and len(self.sent) + 1 == self.crash_at:
            raise RuntimeError("simulated crash mid-batch")
        assert message.to_email is not None
        self.sent.append(message.to_email)
        return SendResult(external_id=f"ext-{message.to_email}")

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        return []

    def fetch_replies(self, since: datetime | None = None) -> list[InboundReply]:
        return []


def _approved_campaign(tmp_path: Path) -> Any:
    p = tmp_path / "p.csv"
    p.write_text(CSV, encoding="utf-8")
    rows = camp.load_prospects_csv(str(p))
    with session_scope() as s:
        cid = camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=rows).id
    with session_scope() as s:
        assert camp.approve(s, campaign_id=cid, approve_all=True) == 5
    return cid


def test_crash_mid_batch_keeps_sent_and_never_resends(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cid = _approved_campaign(tmp_path)

    crashing = RecordingChannel(crash_at=3)
    monkeypatch.setattr(camp, "get_channel", lambda: crashing)
    with pytest.raises(RuntimeError), session_scope() as s:
        camp.send_approved(s, campaign_id=cid)
    assert len(crashing.sent) == 2  # crashed on the 3rd

    # The 2 sends made before the crash are persisted despite the rollback.
    with session_scope() as s:
        sent = [m for m in camp.resolve_campaign(s, str(cid)).members]
        msgs = list(s.query(Message).filter(Message.campaign_id == cid))
        assert sum(1 for m in msgs if m.status == MessageStatus.SENT) == 2
        assert all(m.external_id for m in msgs if m.status == MessageStatus.SENT)
        assert sent  # memberships still readable

    # Re-run: only the 3 remaining go out; the 2 already sent never repeat.
    fresh = RecordingChannel()
    monkeypatch.setattr(camp, "get_channel", lambda: fresh)
    with session_scope() as s:
        assert camp.send_approved(s, campaign_id=cid) == 3
    assert len(fresh.sent) == 3
    assert not set(fresh.sent) & set(crashing.sent)

    with session_scope() as s:
        msgs = list(s.query(Message).filter(Message.campaign_id == cid))
        assert sum(1 for m in msgs if m.status == MessageStatus.SENT) == 5


def test_channel_error_is_committed_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from azul.errors import ChannelError

    cid = _approved_campaign(tmp_path)

    class FailingChannel(RecordingChannel):
        def send(self, message: OutboundMessage) -> SendResult:
            if len(self.sent) == 0 and not getattr(self, "_failed", False):
                self._failed = True
                raise ChannelError("mailbox said no")
            return super().send(message)

    ch = FailingChannel()
    monkeypatch.setattr(camp, "get_channel", lambda: ch)
    with session_scope() as s:
        assert camp.send_approved(s, campaign_id=cid) == 4
    with session_scope() as s:
        msgs = list(s.query(Message).filter(Message.campaign_id == cid))
        assert sum(1 for m in msgs if m.status == MessageStatus.FAILED) == 1
        assert sum(1 for m in msgs if m.status == MessageStatus.SENT) == 4
