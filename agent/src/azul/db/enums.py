"""Back-compat re-export. Canonical enums live in `azul.enums`."""

from azul.enums import (
    CampaignStatus,
    Channel,
    EmailStatus,
    MembershipStatus,
    MessageStatus,
    ReplySentiment,
    ReviewDecision,
)

__all__ = [
    "CampaignStatus",
    "Channel",
    "EmailStatus",
    "MembershipStatus",
    "MessageStatus",
    "ReplySentiment",
    "ReviewDecision",
]
