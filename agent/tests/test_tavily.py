"""Tavily adapter: search + extract mocked, hooks come out in the standard shape."""

from __future__ import annotations

import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import httpx
import pytest
import respx

from azul.config import get_settings
from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError


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


_PRESS: dict[str, Any] = {
    "results": [
        {
            "title": "Interview with Ann Lee",
            "url": "https://techpress.example/ann-lee",
            "content": "Ann Lee explained why Acme refuses to do usage-based pricing.",
            "score": 0.91,
        },
        {
            "title": "Acme blog",
            "url": "https://acme.com/blog/scaling",
            "content": "How we scaled support without scripts.",
            "score": 0.74,
        },
    ]
}
_JOBS: dict[str, Any] = {
    "results": [
        {
            "title": "Acme careers",
            "url": "https://acme.com/careers",
            "content": "Acme is hiring two Account Executives in Paris.",
            "score": 0.8,
        }
    ]
}
_EXTRACT: dict[str, Any] = {
    "results": [
        {"url": "https://acme.com", "raw_content": "Acme home. CRM for plumbers."},
        {"url": "https://acme.com/about", "raw_content": "Founded in a garage in Lyon, 2019."},
    ]
}

_PROSPECT = ProspectBrief(
    email="ann@acme.com", full_name="Ann Lee", company="Acme", company_domain="acme.com"
)


def _mocked_engine() -> Any:
    from azul.research.tavily import TavilyResearchEngine

    return TavilyResearchEngine()


def test_tavily_requires_key() -> None:
    from azul.research.tavily import TavilyResearchEngine

    with env(TAVILY_API_KEY=""), pytest.raises(ConfigError):
        TavilyResearchEngine()


def test_tavily_builds_hooks_from_search_and_extract() -> None:
    with env(TAVILY_API_KEY="k"), respx.mock(base_url="https://api.tavily.com") as router:
        search = router.post("/search").mock(
            side_effect=[httpx.Response(200, json=_PRESS), httpx.Response(200, json=_JOBS)]
        )
        extract = router.post("/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        result = _mocked_engine().research(_PROSPECT)

    assert search.call_count == 2
    assert extract.call_count == 1
    assert result.engine == "tavily"
    texts = [h.text for h in result.hooks]
    assert any("usage-based pricing" in t for t in texts)  # press mention
    assert any(t.startswith("Hiring signal:") for t in texts)  # job postings
    assert any("garage in Lyon" in t for t in texts)  # /about extract
    # The prospect's OWN domain leads (playbook §2): their acme.com blog post
    # outranks a third-party press mention even at a higher raw score.
    top = max(result.hooks, key=lambda h: h.confidence or 0)
    assert top.as_dict()["source_url"] == "https://acme.com/blog/scaling"
    assert top.confidence is not None and top.confidence >= 0.86 - 1e-9
    assert result.hooks[0].source_url == "https://acme.com/blog/scaling"  # own domain first


def test_tavily_extract_includes_blog_url_found_in_search() -> None:
    with env(TAVILY_API_KEY="k"), respx.mock(base_url="https://api.tavily.com") as router:
        router.post("/search").mock(
            side_effect=[httpx.Response(200, json=_PRESS), httpx.Response(200, json=_JOBS)]
        )
        extract = router.post("/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        _mocked_engine().research(_PROSPECT)
    body = extract.calls[0].request.content.decode()
    assert "acme.com/blog/scaling" in body  # blog URL surfaced by search got extracted


def test_tavily_http_error_raises_research_error() -> None:
    with env(TAVILY_API_KEY="k"), respx.mock(base_url="https://api.tavily.com") as router:
        router.post("/search").mock(return_value=httpx.Response(429))
        with pytest.raises(ResearchError):
            _mocked_engine().research(_PROSPECT)


def test_tavily_empty_prospect_returns_no_hooks() -> None:
    with env(TAVILY_API_KEY="k"):
        result = _mocked_engine().research(ProspectBrief(email="x@y.z"))
    assert result.hooks == []


# ── directory exclusion + own-domain priority ───────────────────────────────


def test_directory_helpers() -> None:
    from azul.research.tavily import is_directory_url, is_own_domain

    dirs = {"trustfolio.co", "sortlist.com"}
    assert is_directory_url("https://www.trustfolio.co/agences/pixel", dirs)
    assert is_directory_url("https://fr.sortlist.com/x", dirs)  # subdomain
    assert not is_directory_url("https://pixel.fr/about", dirs)
    assert is_own_domain("https://www.acme.fr/blog", "acme.fr")
    assert is_own_domain("https://blog.acme.fr/x", "acme.fr")  # subdomain of own
    assert not is_own_domain("https://other.fr", "acme.fr")
    assert not is_own_domain("https://acme.fr", None)


def test_directory_press_result_is_never_a_hook() -> None:
    press = {
        "results": [
            {
                "url": "https://www.trustfolio.co/agences/acme",
                "content": "Acme is ranked #3 best agency in our directory.",
                "score": 0.95,
            },
            {
                "url": "https://acme.com/blog/post",
                "content": "Why we dropped per-seat pricing.",
                "score": 0.6,
            },
        ]
    }
    with env(TAVILY_API_KEY="k"), respx.mock(base_url="https://api.tavily.com") as router:
        router.post("/search").mock(
            side_effect=[httpx.Response(200, json=press), httpx.Response(200, json={"results": []})]
        )
        router.post("/extract").mock(return_value=httpx.Response(200, json={"results": []}))
        result = _mocked_engine().research(_PROSPECT)

    urls = [h.source_url for h in result.hooks]
    assert "https://www.trustfolio.co/agences/acme" not in str(urls)  # directory excluded
    assert any("acme.com" in (u or "") for u in urls)  # own-domain hook kept
    assert all("trustfolio" not in (u or "") for u in urls)
