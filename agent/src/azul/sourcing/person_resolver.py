"""Resolve a company's decision-maker before the finder can build email permutations.

Discovery returns companies, often without a named founder. The finder needs a
first+last name to generate candidate addresses, so this step runs FIRST: search
the web for the company's founder/CEO, extract a name + role + confidence via the
existing `chat_json` LLM, and hand it back. Below 0.5 confidence we report nothing
(the pipeline then skips with the explicit reason `no_founder_found`).

Tavily calls are bounded per prospect by PERSON_RESOLVE_MAX_SEARCHES (default 3).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.errors import ConfigError, LLMError, SourcingError
from azul.llm import chat_json
from azul.logging import get_logger

log = get_logger(__name__)

MIN_CONFIDENCE = 0.5
_CONTENT_BUDGET = 5000

_SYSTEM = """\
You identify the founder or top decision-maker (CEO, gérant, dirigeant) of ONE
company from web-page text. Return only what the text supports — do not invent.
Return STRICT JSON: {"founder_name": str, "founder_role": str, "confidence": float}
where confidence is 0-1 (0 = nothing found, 1 = explicitly named). "" if unknown.
"""


@dataclass
class ResolvedPerson:
    founder_name: str | None
    founder_role: str | None
    confidence: float


class PersonResolver(ABC):
    name: ClassVar[str]

    @abstractmethod
    def resolve(self, company: str | None, domain: str | None) -> ResolvedPerson:
        """Find the company's founder/decision-maker (name + role + confidence)."""
        raise NotImplementedError


class TavilyPersonResolver(PersonResolver):
    name: ClassVar[str] = "tavily"

    def __init__(self, timeout: float = 30.0) -> None:
        s = get_settings()
        if not s.tavily_api_key:
            raise ConfigError("TAVILY_API_KEY is required to resolve a company's founder")
        self._max_calls = s.person_resolve_max_searches
        self._client = httpx.Client(
            base_url="https://api.tavily.com",
            headers={"Authorization": f"Bearer {s.tavily_api_key}"},
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

    def _search(self, query: str) -> str:
        data = self._post("/search", {"query": query, "search_depth": "basic", "max_results": 4})
        return "\n".join(str(r.get("content") or "") for r in (data.get("results") or []))

    def _extract(self, urls: list[str]) -> str:
        data = self._post("/extract", {"urls": urls})
        return "\n".join(str(r.get("raw_content") or "") for r in (data.get("results") or []))

    def resolve(self, company: str | None, domain: str | None) -> ResolvedPerson:
        if not company and not domain:
            return ResolvedPerson(None, None, 0.0)
        label = company or domain
        calls = 0
        chunks: list[str] = []
        try:
            for query in (f"fondateur {label}", f"{label} CEO dirigeant"):
                if calls >= self._max_calls:
                    break
                chunks.append(self._search(query))
                calls += 1
            # The company's own /about or team page is the highest-signal source.
            if domain and calls < self._max_calls:
                urls = [f"https://{domain}/about", f"https://{domain}/equipe"]
                chunks.append(self._extract(urls))
                calls += 1
        except httpx.HTTPError as exc:
            if not chunks:
                raise SourcingError(f"Person resolution failed: {exc}") from exc
            log.warning("person_resolve_partial", company=company, error=str(exc))

        content = "\n".join(c for c in chunks if c.strip())[:_CONTENT_BUDGET]
        if not content.strip():
            return ResolvedPerson(None, None, 0.0)
        try:
            data = chat_json(
                [
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": f"Company: {label}\n\nWeb text:\n{content}"},
                ]
            )
        except LLMError as exc:
            log.warning("person_resolve_extract_failed", company=company, error=str(exc))
            return ResolvedPerson(None, None, 0.0)

        name = str(data.get("founder_name") or "").strip() or None
        role = str(data.get("founder_role") or "").strip() or None
        try:
            confidence = max(0.0, min(1.0, float(data.get("confidence", 0.0))))
        except (TypeError, ValueError):
            confidence = 0.0
        log.info("person_resolved", company=company, found=bool(name), confidence=confidence)
        return ResolvedPerson(name, role, confidence)


def get_person_resolver() -> PersonResolver:
    """The configured resolver (Tavily today). Built lazily — needs TAVILY_API_KEY."""
    return TavilyPersonResolver()
