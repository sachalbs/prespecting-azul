"""Stub channel — records a deterministic external id, sends nothing real."""

from __future__ import annotations

from typing import Any, ClassVar

from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.logging import get_logger

log = get_logger(__name__)


class StubChannel(Channel):
    name: ClassVar[str] = "stub"

    def send(self, message: OutboundMessage) -> SendResult:
        log.info(
            "stub_send",
            channel=message.channel,
            to=message.to_email or message.to_handle,
            dedup_key=message.dedup_key,
        )
        return SendResult(external_id=f"stub-{message.dedup_key}", raw={"simulated": True})

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        return []
