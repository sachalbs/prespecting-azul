"""Optional natural-language intent for `azul chat`.

Maps a free-text message to ONE chat command via the configured OpenAI-compatible
Writer model. Returns None when no Writer is configured (or on any failure), so the
chat falls back to the deterministic keyword parser and still works offline.
"""

from __future__ import annotations

import json

import httpx

from azul.config import get_settings
from azul.logging import get_logger

log = get_logger(__name__)

COMMANDS = (
    "campaign",
    "show",
    "approve",
    "edit",
    "send",
    "sync",
    "report",
    "status",
    "follow-up",
    "learn",
    "memory",
    "help",
)

_SYSTEM = (
    "You translate a user's message into ONE Azul command.\n"
    f"Commands: {', '.join(COMMANDS)}.\n"
    'Return STRICT JSON: {"command": <one command>, "args": "<args or empty>"}.\n'
    "Examples:\n"
    ' "lance une campagne sur leads.csv appelée Q1" -> '
    '{"command":"campaign","args":"Q1 from leads.csv"}\n'
    ' "montre les brouillons" -> {"command":"show","args":""}\n'
    ' "approuve le 1 et le 3" -> {"command":"approve","args":"1 3"}\n'
    ' "relance ceux qui n\'ont pas répondu" -> {"command":"follow-up","args":""}'
)


def interpret(line: str) -> str | None:
    s = get_settings()
    if s.writer_provider != "openai_compat" or not (
        s.writer_api_key and s.writer_base_url and s.writer_model
    ):
        return None
    try:
        resp = httpx.post(
            f"{str(s.writer_base_url).rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {s.writer_api_key}"},
            json={
                "model": s.writer_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": line},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
    except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
        log.warning("intent_failed", error=str(exc))
        return None
    command = str(data.get("command", "")).strip()
    if command not in COMMANDS:
        return None
    return f"{command} {str(data.get('args', '')).strip()}".strip()
