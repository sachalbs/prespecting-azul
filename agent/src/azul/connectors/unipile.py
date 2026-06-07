"""Unipile adapter (real skeleton): send from the user's real mailbox + parse replies.

Unipile uses a per-account DSN + X-API-KEY and exposes a unified messaging API
(Outlook/Gmail/LinkedIn/WhatsApp). TODO(unipile-docs): confirm the exact send
endpoint/payload and the reply/bounce webhook schema before going live. Until
then, CHANNEL=stub keeps the loop running.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.enums import Channel as ChannelEnum
from azul.errors import ChannelError, ConfigError
from azul.logging import get_logger

log = get_logger(__name__)


class UnipileChannel(Channel):
    name: ClassVar[str] = "unipile"

    def __init__(self, timeout: float = 30.0) -> None:
        s = get_settings()
        if not (s.unipile_api_key and s.unipile_dsn and s.unipile_account_id):
            raise ConfigError(
                "CHANNEL=unipile requires UNIPILE_API_KEY, UNIPILE_DSN, UNIPILE_ACCOUNT_ID"
            )
        self._account_id = s.unipile_account_id
        self._client = httpx.Client(
            base_url=str(s.unipile_dsn).rstrip("/"),
            headers={"X-API-KEY": s.unipile_api_key, "accept": "application/json"},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def send(self, message: OutboundMessage) -> SendResult:
        if message.channel is not ChannelEnum.EMAIL:
            # TODO(unipile-docs): LinkedIn/WhatsApp use different endpoints.
            raise ChannelError(f"Unipile adapter: {message.channel} not wired yet")
        if not message.to_email:
            raise ChannelError("Email send requires to_email")

        # TODO(unipile-docs): confirm endpoint + payload shape.
        payload: dict[str, Any] = {
            "account_id": self._account_id,
            "to": [{"identifier": message.to_email}],
            "subject": message.subject or "",
            "body": message.body,
        }
        try:
            resp = self._client.post(
                "/api/v1/emails",
                json=payload,
                headers={"X-Idempotency-Key": message.dedup_key},
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            log.error("unipile_send_failed", to=message.to_email, error=str(exc))
            raise ChannelError(f"Unipile send failed: {exc}") from exc

        external_id = str(data.get("id") or data.get("message_id") or "")
        return SendResult(external_id=external_id, raw=data)

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        # TODO(unipile-docs): confirm webhook event types + field names.
        event = payload.get("event") or payload.get("type")
        if event in {"mail_bounced", "bounce"}:
            return [
                InboundReply(
                    text=payload.get("reason", ""),
                    from_email=payload.get("to") or payload.get("recipient"),
                    in_reply_to=payload.get("tracking_id") or payload.get("idempotency_key"),
                    is_bounce=True,
                    bounce_type=payload.get("bounce_type"),
                    raw=payload,
                )
            ]
        if event in {"mail_received", "message_received", "mail_reply"}:
            return [
                InboundReply(
                    text=payload.get("body", "") or payload.get("snippet", ""),
                    from_email=payload.get("from_email") or payload.get("from"),
                    external_id=payload.get("id") or payload.get("message_id"),
                    in_reply_to=payload.get("in_reply_to") or payload.get("tracking_id"),
                    raw=payload,
                )
            ]
        return []
