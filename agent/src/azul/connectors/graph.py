"""Microsoft Graph (Outlook) channel: send from the real mailbox + poll replies.

Send is a create-draft + send so we capture the message id for tracking. Replies
are polled from the inbox and matched to prospects by sender address (Jalon 0).
Sending is always an API call from the real mailbox — never computer-use.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.connectors.base import Channel, InboundReply, OutboundMessage, SendResult
from azul.connectors.graph_auth import acquire_token_silent
from azul.enums import Channel as ChannelEnum
from azul.errors import ChannelError
from azul.logging import get_logger

log = get_logger(__name__)

_BOUNCE_SENDERS = ("postmaster@", "mailer-daemon@")
_BOUNCE_SUBJECTS = ("undeliverable", "delivery status notification", "mail delivery failed")


class GraphChannel(Channel):
    name: ClassVar[str] = "graph"

    def __init__(self, token: str | None = None, timeout: float = 30.0) -> None:
        self._client = httpx.Client(
            base_url="https://graph.microsoft.com/v1.0",
            headers={"Authorization": f"Bearer {token or acquire_token_silent()}"},
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
            raise ChannelError(f"Graph adapter handles email only, got {message.channel}")
        if not message.to_email:
            raise ChannelError("Email send requires to_email")

        draft_body: dict[str, Any] = {
            "subject": message.subject or "",
            "body": {"contentType": "Text", "content": message.body},
            "toRecipients": [{"emailAddress": {"address": message.to_email}}],
            "internetMessageHeaders": [{"name": "x-azul-dedup", "value": message.dedup_key[:128]}],
        }
        try:
            draft = self._client.post("/me/messages", json=draft_body)
            draft.raise_for_status()
            created = draft.json()
            msg_id = created["id"]
            send = self._client.post(f"/me/messages/{msg_id}/send")
            send.raise_for_status()
        except httpx.HTTPError as exc:
            log.error("graph_send_failed", to=message.to_email, error=str(exc))
            raise ChannelError(f"Graph send failed: {exc}") from exc

        external_id = str(created.get("internetMessageId") or created.get("id") or "")
        return SendResult(external_id=external_id, raw=created)

    def fetch_replies(self, since: datetime | None = None) -> list[InboundReply]:
        params: dict[str, str] = {
            "$select": "from,subject,bodyPreview,conversationId,internetMessageId,receivedDateTime",
            "$top": "50",
            "$orderby": "receivedDateTime desc",
        }
        if since is not None:
            iso = since.astimezone().strftime("%Y-%m-%dT%H:%M:%SZ")
            params["$filter"] = f"receivedDateTime ge {iso}"
        try:
            resp = self._client.get("/me/mailFolders/inbox/messages", params=params)
            resp.raise_for_status()
            items = resp.json().get("value", [])
        except httpx.HTTPError as exc:
            raise ChannelError(f"Graph fetch_replies failed: {exc}") from exc

        replies: list[InboundReply] = []
        for it in items:
            addr = (it.get("from", {}).get("emailAddress", {}) or {}).get("address")
            subject = (it.get("subject") or "").lower()
            is_bounce = any(b in (addr or "").lower() for b in _BOUNCE_SENDERS) or any(
                subject.startswith(s) for s in _BOUNCE_SUBJECTS
            )
            replies.append(
                InboundReply(
                    text=it.get("bodyPreview", ""),
                    from_email=addr,
                    external_id=it.get("internetMessageId"),
                    in_reply_to=it.get("conversationId"),
                    is_bounce=is_bounce,
                    bounce_type="ndr" if is_bounce else None,
                    raw=it,
                )
            )
        return replies

    def parse_webhook(self, payload: dict[str, Any]) -> list[InboundReply]:
        # Graph change-notifications would be wired here; Jalon 0 uses polling.
        return []
