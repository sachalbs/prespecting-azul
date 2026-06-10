"""Web discovery: LLM queries -> Tavily search+extract -> candidates, cost-capped."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import httpx
import respx

from azul.config import get_settings
from azul.discovery.brief import ICPBrief
from azul.discovery.web_discovery import WebDiscovery, fallback_queries
from tests.test_brief import writer_env as _writer_only_env


@contextmanager
def writer_env() -> Generator[None, None, None]:
    old = os.environ.get("TAVILY_API_KEY")
    os.environ["TAVILY_API_KEY"] = "tk"
    try:
        with _writer_only_env():
            yield
    finally:
        if old is None:
            os.environ.pop("TAVILY_API_KEY", None)
        else:
            os.environ["TAVILY_API_KEY"] = old
        get_settings.cache_clear()

BRIEF = ICPBrief(
    sells="audit RGPD automatisé",
    sector="agences web",
    company_size="5-30",
    geo="France",
    target_role="fondateur",
    good_prospect="agence e-commerce sans DPO",
    pain_signals=("cookies",),
    tone="direct",
    raw_text="je vends un audit RGPD",
)

WRITER = "https://api.deepseek.com/v1"
TAVILY = "https://api.tavily.com"


def _llm(payload: dict[str, Any]) -> httpx.Response:
    content = json.dumps(payload, ensure_ascii=False)
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _llm_router(router: respx.MockRouter, candidates_batches: list[list[dict[str, str]]]) -> Any:
    """First call = query generation; following calls = extraction batches."""
    replies = [_llm({"queries": ["annuaire agences web france", "top agences web 2026"]})]
    replies += [_llm({"candidates": batch}) for batch in candidates_batches]
    # pad: any further extraction call yields nothing new
    replies += [_llm({"candidates": []})] * 10
    return router.post(f"{WRITER}/chat/completions").mock(side_effect=replies)


_SEARCH = {
    "results": [
        {
            "url": "https://annuaire.example/agences",
            "content": "Agence Alpha (alpha.fr), fondée par Anna Roy. Beta Studio (beta.fr).",
            "score": 0.8,
        }
    ]
}
_EXTRACT = {
    "results": [
        {
            "url": "https://annuaire.example/agences",
            "raw_content": "Liste complète: Gamma Conseil (gamma.fr), dirigée par Gil Marchand...",
        }
    ]
}


def test_discovery_yields_candidates_with_provenance(monkeypatch: Any) -> None:
    batches = [
        [
            {"company_name": "Agence Alpha", "domain": "alpha.fr",
             "founder_name": "Anna Roy", "founder_role": "fondatrice"},
            {"company_name": "Beta Studio", "domain": "https://www.beta.fr",
             "founder_name": "", "founder_role": ""},
        ],
        [
            {"company_name": "Gamma Conseil", "domain": "gamma.fr",
             "founder_name": "Gil Marchand", "founder_role": "CEO"},
        ],
    ]
    with writer_env(), respx.mock() as router:
        _llm_router(router, batches)
        router.post(f"{TAVILY}/search").mock(return_value=httpx.Response(200, json=_SEARCH))
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        out = WebDiscovery().discover(BRIEF, n=2)

    domains = {c.domain for c in out}
    assert {"alpha.fr", "beta.fr", "gamma.fr"} <= domains  # www./https stripped
    alpha = next(c for c in out if c.domain == "alpha.fr")
    assert alpha.founder_name == "Anna Roy"
    assert alpha.source_url is not None and "annuaire" in alpha.source_url
    assert alpha.raw_context  # the evidence travels


def test_tavily_calls_are_capped(monkeypatch: Any) -> None:
    monkeypatch.setenv("DISCOVERY_MAX_SEARCHES", "2")
    from azul.config import get_settings

    get_settings.cache_clear()
    try:
        with writer_env(), respx.mock() as router:
            _llm_router(router, [[{"company_name": "A", "domain": "a.fr",
                                   "founder_name": "", "founder_role": ""}]])
            search = router.post(f"{TAVILY}/search").mock(
                return_value=httpx.Response(200, json=_SEARCH)
            )
            extract = router.post(f"{TAVILY}/extract").mock(
                return_value=httpx.Response(200, json=_EXTRACT)
            )
            WebDiscovery().discover(BRIEF, n=50)  # wants 150, cap stops it
        assert search.call_count + extract.call_count <= 2
    finally:
        get_settings.cache_clear()


def test_oversampling_stops_at_three_times_n() -> None:
    many = [
        {"company_name": f"Boite {i}", "domain": f"boite{i}.fr",
         "founder_name": "", "founder_role": ""}
        for i in range(20)
    ]
    with writer_env(), respx.mock(assert_all_called=False) as router:
        _llm_router(router, [many])
        router.post(f"{TAVILY}/search").mock(return_value=httpx.Response(200, json=_SEARCH))
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        out = WebDiscovery().discover(BRIEF, n=2)
    assert len(out) == 6  # 3x n, not the whole haul


def test_llm_query_failure_falls_back_to_deterministic_queries() -> None:
    with writer_env(), respx.mock() as router:
        # Query-gen LLM call blows up; extraction calls return one candidate.
        replies = [httpx.Response(500)] + [
            _llm({"candidates": [{"company_name": "A", "domain": "a.fr",
                                  "founder_name": "", "founder_role": ""}]})
        ] * 10
        router.post(f"{WRITER}/chat/completions").mock(side_effect=replies)
        search = router.post(f"{TAVILY}/search").mock(
            return_value=httpx.Response(200, json=_SEARCH)
        )
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        out = WebDiscovery().discover(BRIEF, n=1)
    assert search.called  # deterministic fallback queries still searched
    assert any(c.domain == "a.fr" for c in out)
    assert fallback_queries(BRIEF)[0].startswith("annuaire")


def test_no_duplicate_domains_within_a_batch() -> None:
    dup = [
        {"company_name": "Alpha", "domain": "alpha.fr", "founder_name": "", "founder_role": ""},
        {"company_name": "Alpha encore", "domain": "www.alpha.fr",
         "founder_name": "", "founder_role": ""},
    ]
    with writer_env(), respx.mock() as router:
        _llm_router(router, [dup, dup])
        router.post(f"{TAVILY}/search").mock(return_value=httpx.Response(200, json=_SEARCH))
        router.post(f"{TAVILY}/extract").mock(return_value=httpx.Response(200, json=_EXTRACT))
        out = WebDiscovery().discover(BRIEF, n=5)
    assert [c.domain for c in out].count("alpha.fr") == 1
