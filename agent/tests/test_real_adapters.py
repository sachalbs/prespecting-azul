"""Unit tests for the real adapters — all HTTP mocked, no network."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import httpx
import respx

from azul.config import get_settings
from azul.connectors.base import OutboundMessage
from azul.connectors.graph import GraphChannel
from azul.enums import Channel, EmailStatus


@contextmanager
def env(**kv: str) -> Generator[None, None, None]:
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


# ── Prospeo enrich (sourcing) ───────────────────────────────────────────────

_PROSPEO_OK: dict[str, Any] = {
    "error": False,
    "person": {
        "headline": "Building Fin.ai",
        "current_job_title": "CEO",
        "linkedin_url": "https://linkedin.com/in/jane",
        "job_history": [{"title": "CEO", "company_name": "Acme", "current": True}],
        "email": {"status": "VERIFIED", "email": "jane.doe@acme.com", "revealed": True},
    },
    "company": {
        "description_ai": "Acme builds X.",
        "keywords": ["saas", "ai"],
        "funding": {"funding_events": [{"stage": "Series B", "amount_printed": "$20M"}]},
        "job_postings": {"active_titles": ["account executive"]},
    },
}


def test_prospeo_enrich_returns_verified_email_and_dossier() -> None:
    from azul.sourcing.providers.prospeo import ProspeoVerifier

    with env(PROSPEO_API_KEY="k"), respx.mock(base_url="https://api.prospeo.io") as router:
        router.post("/enrich-person").mock(return_value=httpx.Response(200, json=_PROSPEO_OK))
        result = ProspeoVerifier().verify("", full_name="Jane Doe", company_domain="acme.com")
    assert result.status == EmailStatus.VERIFIED
    assert result.email == "jane.doe@acme.com"
    assert result.dossier["current_title"] == "CEO"
    assert result.dossier["latest_funding"]["stage"] == "Series B"


def test_prospeo_masked_email_is_risky() -> None:
    from azul.sourcing.providers.prospeo import ProspeoVerifier

    masked = {
        **_PROSPEO_OK,
        "person": {
            **_PROSPEO_OK["person"],
            "email": {"status": "VERIFIED", "email": "jane.****@acme.com"},
        },
    }
    with env(PROSPEO_API_KEY="k"), respx.mock(base_url="https://api.prospeo.io") as router:
        router.post("/enrich-person").mock(return_value=httpx.Response(200, json=masked))
        result = ProspeoVerifier().verify("", full_name="Jane Doe", company_domain="acme.com")
    assert result.status == EmailStatus.RISKY


# ── MS Graph (connector) ────────────────────────────────────────────────────


def test_graph_send_creates_draft_then_sends() -> None:
    with respx.mock(base_url="https://graph.microsoft.com/v1.0") as router:
        router.post("/me/messages").mock(
            return_value=httpx.Response(201, json={"id": "AAA", "internetMessageId": "<m1>"})
        )
        router.post("/me/messages/AAA/send").mock(return_value=httpx.Response(202))
        ch = GraphChannel(token="fake")
        result = ch.send(
            OutboundMessage(
                channel=Channel.EMAIL,
                body="hi",
                dedup_key="d1",
                to_email="jane@acme.com",
                subject="quick one",
            )
        )
    assert result.external_id == "<m1>"


def test_graph_fetch_replies_parses_and_flags_bounce() -> None:
    inbox = {
        "value": [
            {
                "from": {"emailAddress": {"address": "jane@acme.com"}},
                "subject": "Re: quick one",
                "bodyPreview": "sure, let's talk",
                "conversationId": "C1",
                "internetMessageId": "<r1>",
            },
            {
                "from": {"emailAddress": {"address": "postmaster@acme.com"}},
                "subject": "Undeliverable: quick one",
                "bodyPreview": "failed",
                "internetMessageId": "<b1>",
            },
        ]
    }
    with respx.mock(base_url="https://graph.microsoft.com/v1.0") as router:
        router.get("/me/mailFolders/inbox/messages").mock(
            return_value=httpx.Response(200, json=inbox)
        )
        replies = GraphChannel(token="fake").fetch_replies()
    assert len(replies) == 2
    assert replies[0].from_email == "jane@acme.com" and not replies[0].is_bounce
    assert replies[1].is_bounce


# ── chat NL intent (Writer LLM) ─────────────────────────────────────────────


def test_interpret_maps_free_text_to_command() -> None:
    from azul.cli.intent import interpret

    payload = {"choices": [{"message": {"content": '{"command":"approve","args":"1 3"}'}}]}
    with (
        env(
            WRITER_PROVIDER="openai_compat",
            WRITER_BASE_URL="https://llm.test/v1",
            WRITER_MODEL="m",
            WRITER_API_KEY="k",
        ),
        respx.mock(base_url="https://llm.test/v1") as router,
    ):
        router.post("/chat/completions").mock(return_value=httpx.Response(200, json=payload))
        assert interpret("approuve le 1 et le 3") == "approve 1 3"


def test_interpret_returns_none_without_writer() -> None:
    from azul.cli.intent import interpret

    assert interpret("n'importe quoi") is None  # stub mode: no openai_compat writer


# ── Writer over an OpenAI-compatible API (e.g. Mistral) ─────────────────────


def test_openai_compat_writer_parses_a_draft() -> None:
    from azul.domain import ProspectBrief
    from azul.writing.base import DraftRequest
    from azul.writing.openai_compat import OpenAICompatWriter

    content = '{"subject":"quick one","body":"Hi Ann, saw the raise.","angle":"funding"}'
    payload = {"choices": [{"message": {"content": content}}]}
    with (
        env(
            WRITER_PROVIDER="openai_compat",
            WRITER_BASE_URL="https://api.mistral.ai/v1",
            WRITER_MODEL="mistral-large-latest",
            WRITER_API_KEY="k",
        ),
        respx.mock(base_url="https://api.mistral.ai/v1") as router,
    ):
        router.post("/chat/completions").mock(return_value=httpx.Response(200, json=payload))
        draft = OpenAICompatWriter().write(
            DraftRequest(
                prospect=ProspectBrief(email="a@b.com", full_name="Ann Lee"), hook="funding"
            )
        )
    assert draft.subject == "quick one"
    assert draft.angle == "funding"
