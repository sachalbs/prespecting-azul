"""Telegram operator channel — the chat surface over Telegram (official, free).

Pipes Telegram messages to `ChatSession` (the same brain the CLI `chat` uses).
Each Telegram chat is its own tenant, so users are isolated. Long-poll for the
beta (no public URL needed); `handle_update` also backs a webhook in production.
WhatsApp (official Cloud API) will plug into the same `handle_update` later.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from azul.cli.chat import ChatSession
from azul.config import get_settings
from azul.errors import ConfigError
from azul.logging import get_logger

log = get_logger(__name__)

_MAX_LEN = 4096  # Telegram message limit


def _chunks(text: str, n: int = _MAX_LEN) -> list[str]:
    return [text[i : i + n] for i in range(0, len(text), n)] or [""]


class TelegramBot:
    def __init__(self, token: str | None = None, timeout: float = 65.0) -> None:
        token = token or get_settings().telegram_bot_token
        if not token:
            raise ConfigError("TELEGRAM_BOT_TOKEN required for the Telegram bot")
        self._client = httpx.Client(
            base_url=f"https://api.telegram.org/bot{token}", timeout=timeout
        )
        # chat_id -> session (in-memory; fine for beta, persist later)
        self.sessions: dict[int, ChatSession] = {}

    def _session_for(self, chat_id: int) -> ChatSession:
        session = self.sessions.get(chat_id)
        if session is None:
            session = ChatSession(tenant=f"tg-{chat_id}")
            self.sessions[chat_id] = session
        return session

    def send_message(self, chat_id: int, text: str) -> None:
        for chunk in _chunks(text):
            self._client.post("/sendMessage", json={"chat_id": chat_id, "text": chunk})

    def handle_update(self, update: dict[str, Any]) -> str | None:
        """Route one Telegram update to its ChatSession and reply. Returns the reply."""
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text")
        if chat_id is None or not text:
            return None
        reply = self._session_for(int(chat_id)).handle(str(text)) or "…"
        self.send_message(int(chat_id), reply)
        return reply

    def poll(self) -> None:
        """Long-poll getUpdates and dispatch. Beta runner; webhook uses handle_update."""
        log.info("telegram_poll_start")
        offset = 0
        while True:
            try:
                resp = self._client.get(
                    "/getUpdates", params={"timeout": 50, "offset": offset}
                )
                resp.raise_for_status()
                for update in resp.json().get("result", []):
                    offset = update["update_id"] + 1
                    self.handle_update(update)
            except httpx.HTTPError as exc:
                # Never log str(exc): httpx messages embed the URL, which carries the token.
                log.warning("telegram_poll_error", error=type(exc).__name__)
                time.sleep(3)
