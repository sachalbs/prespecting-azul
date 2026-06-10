"""Episodic memory: persist and match outcomes. The raw material of the flywheel."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from azul.connectors.base import InboundReply
from azul.db.models import Message, Outcome
from azul.enums import MembershipStatus, MessageStatus, ReplySentiment
from azul.logging import get_logger

log = get_logger(__name__)


class EpisodicMemory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record_outcome(
        self,
        *,
        message_id: uuid.UUID,
        replied: bool = False,
        reply_sentiment: ReplySentiment | None = None,
        reply_text: str | None = None,
        meeting_booked: bool = False,
        bounced: bool = False,
        bounce_type: str | None = None,
        raw_event: dict[str, object] | None = None,
    ) -> Outcome:
        outcome = Outcome(
            message_id=message_id,
            replied=replied,
            replied_at=datetime.now(tz=UTC) if replied else None,
            reply_sentiment=reply_sentiment,
            reply_text=reply_text,
            meeting_booked=meeting_booked,
            bounced=bounced,
            bounce_type=bounce_type,
            raw_event=raw_event or {},
        )
        self.session.add(outcome)
        log.info(
            "outcome_recorded",
            message_id=str(message_id),
            replied=replied,
            bounced=bounced,
            sentiment=reply_sentiment,
        )
        return outcome

    def _match_message(self, reply: InboundReply) -> Message | None:
        """Resolve an inbound reply to the message we sent (by external id / dedup key)."""
        if reply.in_reply_to:
            stmt = select(Message).where(
                (Message.external_id == reply.in_reply_to)
                | (Message.dedup_key == reply.in_reply_to)
            )
            msg = self.session.scalars(stmt).first()
            if msg:
                return msg
        if reply.from_email:
            stmt = (
                select(Message)
                .join(Message.prospect)
                .where(Message.prospect.has(email=reply.from_email))
                .order_by(Message.sent_at.desc())
            )
            return self.session.scalars(stmt).first()
        return None

    def _already_ingested(self, message: Message, reply: InboundReply) -> bool:
        """True if this inbound item already produced an outcome (idempotent polling)."""
        inbound_id = reply.external_id or reply.raw.get("internetMessageId")
        if not inbound_id:
            return False
        return any(o.raw_event.get("internetMessageId") == inbound_id for o in message.outcomes)

    def ingest_reply(self, reply: InboundReply) -> Outcome | None:
        """Attach an inbound reply/bounce to its message as an outcome."""
        message = self._match_message(reply)
        if message is None:
            log.warning("reply_unmatched", from_email=reply.from_email)
            return None
        if self._already_ingested(message, reply):
            log.info("reply_duplicate_skipped", message_id=str(message.id))
            return None

        outcome = self.record_outcome(
            message_id=message.id,
            replied=not reply.is_bounce,
            reply_text=reply.text or None,
            bounced=reply.is_bounce,
            bounce_type=reply.bounce_type,
            raw_event=reply.raw,
        )
        if not reply.is_bounce:
            self._mark_replied(message)
        return outcome

    def _mark_replied(self, message: Message) -> None:
        from azul.db.models import CampaignProspect

        stmt = select(CampaignProspect).where(
            CampaignProspect.campaign_id == message.campaign_id,
            CampaignProspect.prospect_id == message.prospect_id,
        )
        membership = self.session.scalars(stmt).first()
        if membership:
            membership.status = MembershipStatus.REPLIED

    def recall(self, prospect_id: uuid.UUID) -> str | None:
        """A one-line relationship memory: have we touched this person before?"""
        sent = self.session.scalars(
            select(Message)
            .where(Message.prospect_id == prospect_id, Message.status == MessageStatus.SENT)
            .order_by(Message.sent_at.desc())
        ).all()
        if not sent:
            return None
        last = sent[0]
        replied = (
            self.session.scalar(
                select(func.count())
                .select_from(Outcome)
                .join(Message)
                .where(Message.prospect_id == prospect_id, Outcome.replied.is_(True))
            )
            or 0
        )
        when = last.sent_at.date().isoformat() if last.sent_at else "before"
        mood = "they replied before (warm)" if replied else "no reply yet"
        return (
            f"You've reached this person {len(sent)}x before "
            f"(last angle '{last.angle or 'n/a'}', {when}); {mood}. Don't repeat yourself."
        )
