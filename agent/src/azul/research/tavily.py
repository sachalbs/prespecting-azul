"""Tavily research — cheap web search + page extract, no browser, no LLM.

Tier 1 of the staged research: one basic search on the person (press mentions,
posts, interviews), one on hiring signals, plus an extract pass over the company
site (root + /about + a blog URL when one surfaces). Each finding becomes a
standard `Hook` (same structure Holo emits), confidence mapped from Tavily's
relevance score, so the router can compare tiers apples-to-apples.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError
from azul.logging import get_logger
from azul.research.base import Hook, ResearchEngine, ResearchResult

log = get_logger(__name__)

_SNIPPET_LEN = 240


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return text[:_SNIPPET_LEN]


class TavilyResearchEngine(ResearchEngine):
    name: ClassVar[str] = "tavily"

    def __init__(self, timeout: float = 30.0) -> None:
        key = get_settings().tavily_api_key
        if not key:
            raise ConfigError("TAVILY_API_KEY is required for RESEARCH_ENGINE=tavily/tiered")
        self._client = httpx.Client(
            base_url="https://api.tavily.com",
            headers={"Authorization": f"Bearer {key}"},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        resp = self._client.post(path, json=payload)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data

    def _search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        data = self._post(
            "/search",
            {"query": query, "search_depth": "basic", "max_results": max_results},
        )
        return list(data.get("results") or [])

    def _extract(self, urls: list[str]) -> list[dict[str, Any]]:
        if not urls:
            return []
        data = self._post("/extract", {"urls": urls})
        return list(data.get("results") or [])

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        who = " ".join(filter(None, [prospect.full_name, prospect.company]))
        domain = (prospect.company_domain or "").strip().lower()
        if not who and not domain:
            return ResearchResult(engine=self.name, hooks=[], sources=[], raw={})

        hooks: list[Hook] = []
        sources: list[dict[str, Any]] = []
        raw: dict[str, Any] = {}
        try:
            # Press / posts / interviews about the person.
            press: list[dict[str, Any]] = []
            if who:
                press = self._search(f'"{prospect.full_name}" {prospect.company or domain}')
            raw["press"] = press
            for r in press:
                content = r.get("content") or ""
                if not content:
                    continue
                hooks.append(
                    Hook(
                        text=_snippet(content),
                        rationale="Web/press mention found by search.",
                        source_url=r.get("url"),
                        confidence=min(0.85, float(r.get("score") or 0.0)),
                    )
                )
                sources.append({"url": r.get("url"), "type": "search"})

            # Hiring signals.
            if prospect.company or domain:
                jobs = self._search(f"{prospect.company or domain} jobs hiring careers", 3)
                raw["jobs"] = jobs
                top_job = next((r for r in jobs if r.get("content")), None)
                if top_job is not None:
                    hooks.append(
                        Hook(
                            text=f"Hiring signal: {_snippet(top_job['content'])}",
                            rationale="Active job postings — likely scaling that function.",
                            source_url=top_job.get("url"),
                            confidence=0.55,
                        )
                    )
                    sources.append({"url": top_job.get("url"), "type": "jobs"})

            # The company's own site: root + /about (+ first blog URL search surfaced).
            if domain:
                urls = [f"https://{domain}", f"https://{domain}/about"]
                blog = next(
                    (r.get("url") for r in raw.get("press", []) if "/blog" in (r.get("url") or "")),
                    None,
                )
                if blog:
                    urls.append(str(blog))
                extracted = self._extract(urls)
                raw["extract"] = [
                    {"url": e.get("url"), "raw_content": (e.get("raw_content") or "")[:2000]}
                    for e in extracted
                ]
                about = next(
                    (e for e in extracted if "/about" in (e.get("url") or "")),
                    next(iter(extracted), None),
                )
                if about is not None and about.get("raw_content"):
                    hooks.append(
                        Hook(
                            text=f'Their site says: "{_snippet(about["raw_content"])}"',
                            rationale="From the company's own site.",
                            source_url=about.get("url"),
                            confidence=0.45,
                        )
                    )
                    sources.append({"url": about.get("url"), "type": "extract"})
        except httpx.HTTPError as exc:
            log.error("tavily_failed", email=prospect.email, error=str(exc))
            raise ResearchError(f"Tavily research failed: {exc}") from exc

        log.info("tavily_done", email=prospect.email, hooks=len(hooks))
        return ResearchResult(engine=self.name, hooks=hooks, sources=sources, raw=raw)
