"""`Channel` — send a touch and parse inbound replies. Adapter = Unipile in v0."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from azul.enums import Channel as ChannelEnum


@dataclass
class OutboundMessage:
    channel: ChannelEnum
    body: str
    dedup_key: str  # idempotency: the connector must not double-send this
    to_email: str | None = None
    to_handle: str | None = None
    subject: str | None = None


@dataclass
class SendResult:
    external_id: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class InboundReply:
    text: str
    from_email: str | None = None
    external_id: str | None = None  # provider id of the inbound item
    in_reply_to: str | None = None  # external_id of our sent message, if known
    is_bounce: bool = False
    bounce_type: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class Channel(ABC):
    name: ClassVar[str]

    @abstractmethod
    def send(self, message: OutboundMessage) -> SendResult:
        raise NotImplementedError

    @abstractmethod
    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        """Turn a provider reply/bounce webhook into normalised inbound events."""
        raise NotImplementedError
