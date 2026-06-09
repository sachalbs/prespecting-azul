"""Telegram operator transport: routes messages to ChatSession (HTTP mocked)."""

from __future__ import annotations

from typing import Any

import httpx
import respx

from azul.chatops.telegram import TelegramBot

_BASE = "https://api.telegram.org/botT"


def _update(chat_id: int, text: str) -> dict[str, Any]:
    return {"update_id": chat_id, "message": {"chat": {"id": chat_id}, "text": text}}


def test_update_routes_to_chatsession_and_sends_reply() -> None:
    with respx.mock(base_url=_BASE) as router:
        route = router.post("/sendMessage").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        reply = TelegramBot(token="T").handle_update(_update(123, "help"))
    assert reply is not None and "campaign" in reply.lower()
    assert route.called


def test_sessions_are_isolated_per_chat() -> None:
    with respx.mock(base_url=_BASE) as router:
        router.post("/sendMessage").mock(return_value=httpx.Response(200, json={"ok": True}))
        bot = TelegramBot(token="T")
        bot.handle_update(_update(1, "help"))
        bot.handle_update(_update(1, "help"))
        bot.handle_update(_update(2, "help"))
    assert set(bot.sessions) == {1, 2}
    assert bot.sessions[1].tenant == "tg-1"


def test_non_message_update_is_ignored() -> None:
    assert TelegramBot(token="T").handle_update({"update_id": 1}) is None
