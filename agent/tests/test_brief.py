"""Conversational brief: one question at a time, capped exchanges, persisted."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
import respx

from azul.config import get_settings
from azul.discovery.brief import BriefSession, load_latest_brief, save_brief

BASE = "https://api.deepseek.com/v1"


@contextmanager
def writer_env() -> Generator[None, None, None]:
    kv = {
        "WRITER_BASE_URL": BASE,
        "WRITER_MODEL": "deepseek-chat",
        "WRITER_API_KEY": "k",
    }
    old = {k: os.environ.get(k) for k in kv}
    os.environ.update(kv)
    get_settings.cache_clear()
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        get_settings.cache_clear()


def _llm(payload: dict[str, Any]) -> httpx.Response:
    content = json.dumps(payload, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


_FINAL_BRIEF = {
    "done": True,
    "brief": {
        "sells": "audit RGPD automatisé",
        "sector": "agences web",
        "company_size": "5-30",
        "geo": "France",
        "target_role": "fondateur",
        "good_prospect": "agence avec clients e-commerce, pas de DPO",
        "pain_signals": ["mentions légales obsolètes", "pas de bannière cookies"],
        "tone": "direct, pair à pair",
    },
}


def test_brief_in_four_answers_fills_key_fields() -> None:
    replies = [
        _llm({"done": False, "question": "Tu vends ça à qui, précisément ?"}),
        _llm({"done": False, "question": "Quelle taille de boîte vise-t-on ?"}),
        _llm({"done": False, "question": "À quoi ressemble ton client idéal ?"}),
        _llm(_FINAL_BRIEF),
    ]
    with writer_env(), respx.mock(base_url=BASE) as router:
        router.post("/chat/completions").mock(side_effect=replies)
        s = BriefSession()
        q1 = s.start("je vends un audit RGPD automatisé pour les agences web")
        assert q1 is not None and "?" in q1
        q2 = s.reply("aux fondateurs d'agences web en France")
        q3 = s.reply("5 à 30 personnes")
        assert q2 and q3 and not s.done
        assert s.reply("une agence avec des clients e-commerce et pas de DPO") is None

    assert s.done
    brief = s.brief
    assert brief is not None
    assert brief.sells and brief.sector and brief.geo and brief.target_role
    assert brief.company_size == "5-30"
    assert len(brief.pain_signals) == 2
    assert "audit RGPD" in brief.raw_text  # the user's own words are kept


def test_brief_is_forced_to_finalise_at_the_cap() -> None:
    bodies: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.read().decode())
        if len(bodies) < 3:
            return _llm({"done": False, "question": f"Question {len(bodies)} ?"})
        return _llm(_FINAL_BRIEF)

    with writer_env(), respx.mock(base_url=BASE) as router:
        router.post("/chat/completions").mock(side_effect=handler)
        s = BriefSession(max_exchanges=3)
        s.start("je vends un truc")
        s.reply("réponse 1")
        assert s.reply("réponse 2") is None  # cap hit -> forced finalisation

    assert s.done
    assert "Finalise NOW" in bodies[-1]  # the forcing instruction was sent


def test_brief_without_question_or_done_closes_with_best_effort() -> None:
    with writer_env(), respx.mock(base_url=BASE) as router:
        router.post("/chat/completions").mock(
            return_value=_llm({"done": False, "brief": {"sells": "x"}})
        )
        s = BriefSession()
        assert s.start("brief minimal") is None
    assert s.done and s.brief is not None and s.brief.sells == "x"


def test_chat_json_requires_writer_config() -> None:
    from azul.errors import ConfigError
    from azul.llm import chat_json

    old = os.environ.pop("WRITER_API_KEY", None)
    get_settings.cache_clear()
    try:
        with pytest.raises(ConfigError):
            chat_json([{"role": "user", "content": "hi"}])
    finally:
        if old is not None:
            os.environ["WRITER_API_KEY"] = old
        get_settings.cache_clear()


def test_brief_persisted_and_reloaded_as_targeting_memory() -> None:
    from azul.db.session import session_scope
    from azul.orchestrator.campaign import ensure_tenant

    replies = [_llm(_FINAL_BRIEF)]
    with writer_env(), respx.mock(base_url=BASE) as router:
        router.post("/chat/completions").mock(side_effect=replies)
        s = BriefSession()
        s.start("je vends un audit RGPD automatisé")
    brief = s.brief
    assert brief is not None

    with session_scope() as db:
        tenant = ensure_tenant(db, "t1")
        save_brief(db, tenant.id, brief)
        tid = tenant.id
    with session_scope() as db:
        loaded = load_latest_brief(db, tid)
        assert loaded is not None
        assert loaded.sells == brief.sells
        assert loaded.pain_signals == brief.pain_signals
        assert loaded.raw_text == "je vends un audit RGPD automatisé"
