"""ORM models — multi-tenant + flywheel-ready from day one (1 tenant in v0).

`outcomes` is the learning log. `skills` is the procedural store (filled later).
Every table carries `tenant_id` so row isolation / RLS slots in without a rewrite.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from azul.config import get_settings
from azul.db.base import Base, TimestampMixin, UUIDMixin, vector_type
from azul.enums import (
    CampaignStatus,
    Channel,
    EmailStatus,
    MembershipStatus,
    MessageStatus,
    ReplySentiment,
    ReviewDecision,
    VerifyStatus,
)


def _enum(enum_cls: type) -> Enum:
    return Enum(enum_cls, native_enum=False, validate_strings=True, length=32)


class Tenant(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    campaigns: Mapped[list[Campaign]] = relationship(back_populates="tenant")
    prospects: Mapped[list[Prospect]] = relationship(back_populates="tenant")


class Campaign(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "campaigns"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[CampaignStatus] = mapped_column(
        _enum(CampaignStatus), default=CampaignStatus.DRAFT
    )
    # Discovered leads awaiting list approval (ICP-brief flow): [{full_name, company, …}]
    leads: Mapped[list[dict[str, Any]]] = mapped_column(default=list)

    tenant: Mapped[Tenant] = relationship(back_populates="campaigns")
    members: Mapped[list[CampaignProspect]] = relationship(back_populates="campaign")


class Prospect(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "prospects"
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_prospect_tenant_email"),)

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    email: Mapped[str] = mapped_column(String(320), index=True)
    email_status: Mapped[EmailStatus] = mapped_column(
        _enum(EmailStatus), default=EmailStatus.UNKNOWN
    )
    # Raw verdict + confidence from the in-house verifier (MX + SMTP handshake).
    verify_status: Mapped[VerifyStatus | None] = mapped_column(
        _enum(VerifyStatus), default=None
    )
    verify_confidence: Mapped[float | None] = mapped_column(Float, default=None)
    full_name: Mapped[str | None] = mapped_column(String(200), default=None)
    title: Mapped[str | None] = mapped_column(String(200), default=None)
    company: Mapped[str | None] = mapped_column(String(200), default=None)
    company_domain: Mapped[str | None] = mapped_column(String(255), default=None)
    segment: Mapped[str | None] = mapped_column(String(120), index=True, default=None)
    signals: Mapped[dict[str, Any]] = mapped_column(default=dict)
    source: Mapped[str | None] = mapped_column(String(120), default=None)

    tenant: Mapped[Tenant] = relationship(back_populates="prospects")
    research: Mapped[list[Research]] = relationship(back_populates="prospect")
    messages: Mapped[list[Message]] = relationship(back_populates="prospect")


class CampaignProspect(UUIDMixin, TimestampMixin, Base):
    """Membership: where a prospect sits within a given campaign."""

    __tablename__ = "campaign_prospects"
    __table_args__ = (UniqueConstraint("campaign_id", "prospect_id", name="uq_membership"),)

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), index=True)
    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id"), index=True)
    status: Mapped[MembershipStatus] = mapped_column(
        _enum(MembershipStatus), default=MembershipStatus.PENDING
    )

    campaign: Mapped[Campaign] = relationship(back_populates="members")


class Research(UUIDMixin, TimestampMixin, Base):
    """Deep-research output for one prospect: the hook(s) + provenance + raw."""

    __tablename__ = "research"

    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id"), default=None)
    engine: Mapped[str] = mapped_column(String(60))
    # Which tier of the staged router produced the retained hooks (tier1=Tavily,
    # tier2=Holo) — measures the real Tier1/Tier2 ratio.
    tier: Mapped[str | None] = mapped_column(String(20), default=None)
    top_hook: Mapped[str | None] = mapped_column(Text, default=None)
    hooks: Mapped[list[dict[str, Any]]] = mapped_column(default=list)
    sources: Mapped[list[dict[str, Any]]] = mapped_column(default=list)
    raw: Mapped[dict[str, Any]] = mapped_column(default=dict)

    prospect: Mapped[Prospect] = relationship(back_populates="research")


class Message(UUIDMixin, TimestampMixin, Base):
    """A drafted/sent touch. Human approval + edits captured inline (flywheel signal).

    Follow-ups are modelled as child messages via parent_message_id + step.
    Idempotent: dedup_key is unique; we never double-send.
    """

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("dedup_key", name="uq_message_dedup"),
        UniqueConstraint("campaign_id", "prospect_id", "step", name="uq_message_step"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    prospect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("prospects.id"), index=True)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id"), index=True)
    parent_message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("messages.id"), default=None
    )
    step: Mapped[int] = mapped_column(Integer, default=1)

    channel: Mapped[Channel] = mapped_column(_enum(Channel), default=Channel.EMAIL)
    angle: Mapped[str | None] = mapped_column(String(120), default=None)
    subject: Mapped[str | None] = mapped_column(String(400), default=None)
    body: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[MessageStatus] = mapped_column(_enum(MessageStatus), default=MessageStatus.DRAFT)
    dedup_key: Mapped[str] = mapped_column(String(200))

    # Human-in-the-loop capture
    review_decision: Mapped[ReviewDecision | None] = mapped_column(
        _enum(ReviewDecision), default=None
    )
    human_edited_body: Mapped[str | None] = mapped_column(Text, default=None)
    approved_by: Mapped[str | None] = mapped_column(String(200), default=None)
    approved_at: Mapped[datetime | None] = mapped_column(default=None)

    # Send bookkeeping
    sent_at: Mapped[datetime | None] = mapped_column(default=None)
    external_id: Mapped[str | None] = mapped_column(String(255), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)

    prospect: Mapped[Prospect] = relationship(back_populates="messages")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="message")

    @property
    def final_body(self) -> str:
        return self.human_edited_body or self.body


class Outcome(UUIDMixin, TimestampMixin, Base):
    """THE learning log: what happened to a touch. One row per inbound signal."""

    __tablename__ = "outcomes"

    message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), index=True)
    replied: Mapped[bool] = mapped_column(Boolean, default=False)
    replied_at: Mapped[datetime | None] = mapped_column(default=None)
    reply_sentiment: Mapped[ReplySentiment | None] = mapped_column(
        _enum(ReplySentiment), default=None
    )
    reply_text: Mapped[str | None] = mapped_column(Text, default=None)
    meeting_booked: Mapped[bool] = mapped_column(Boolean, default=False)
    bounced: Mapped[bool] = mapped_column(Boolean, default=False)
    bounce_type: Mapped[str | None] = mapped_column(String(60), default=None)
    raw_event: Mapped[dict[str, Any]] = mapped_column(default=dict)

    message: Mapped[Message] = relationship(back_populates="outcomes")


class Skill(UUIDMixin, TimestampMixin, Base):
    """Procedural memory: winning patterns by segment. De-identified, filled later.

    tenant_id NULL == cross-customer pattern, pooled at segment level only.
    """

    __tablename__ = "skills"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id"), default=None, index=True
    )
    segment: Mapped[str] = mapped_column(String(120), index=True)
    channel: Mapped[Channel | None] = mapped_column(_enum(Channel), default=None)
    pattern: Mapped[str] = mapped_column(Text)
    win_rate: Mapped[float | None] = mapped_column(Float, default=None)
    eval_score: Mapped[float | None] = mapped_column(Float, default=None)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    embedding: Mapped[list[float] | None] = mapped_column(
        vector_type(get_settings().embedding_dim), default=None
    )


class ConnectedAccount(UUIDMixin, TimestampMixin, Base):
    """Per-tenant OAuth credentials for a connected mailbox/channel (multi-tenant)."""

    __tablename__ = "connected_accounts"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_connected_tenant_provider"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40))
    account_email: Mapped[str | None] = mapped_column(String(320), default=None)
    refresh_token: Mapped[str] = mapped_column(Text)
