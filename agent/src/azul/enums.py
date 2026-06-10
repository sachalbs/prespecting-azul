"""Domain enums, ORM-free so any module/adapter can use them.

Persisted as checked VARCHAR (native_enum=False) by the ORM, for portability.
"""

from __future__ import annotations

from enum import StrEnum


class EmailStatus(StrEnum):
    UNKNOWN = "unknown"
    VERIFIED = "verified"
    RISKY = "risky"
    INVALID = "invalid"


class VerifyStatus(StrEnum):
    """Raw verdict from the in-house verifier (MX + SMTP handshake)."""

    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    UNKNOWN = "unknown"


class Channel(StrEnum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"


class CampaignStatus(StrEnum):
    DRAFT = "draft"
    DISCOVERED = "discovered"  # leads found, awaiting human list approval
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    SENDING = "sending"
    DONE = "done"


class MembershipStatus(StrEnum):
    PENDING = "pending"
    RESEARCHED = "researched"
    DRAFTED = "drafted"
    APPROVED = "approved"
    SENT = "sent"
    REPLIED = "replied"
    SKIPPED = "skipped"
    FAILED = "failed"


class MessageStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    EDIT = "edit"
    REJECT = "reject"


class ReplySentiment(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    OUT_OF_OFFICE = "out_of_office"
    UNSUBSCRIBE = "unsubscribe"
