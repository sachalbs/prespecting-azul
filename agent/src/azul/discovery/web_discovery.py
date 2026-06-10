"""Web discovery: ICPBrief -> search queries (LLM) -> Tavily search+extract -> candidates.

DeepSeek turns the brief into diverse queries (directories, rankings, sector
lists, "agences growth FR"-style); Tavily fetches; DeepSeek mines the page
content into `ProspectCandidate`s. Oversamples ~3x n so enough survives scoring
and dedup. Cost is bounded: every Tavily call (search OR extract) counts toward
DISCOVERY_MAX_SEARCHES (default 15).
"""

from __future__ import annotations

import re
from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.discovery.base import CandidateDiscovery, ProspectCandidate
from azul.discovery.brief import ICPBrief
from azul.errors import ConfigError, LLMError, SourcingError
from azul.llm import chat_json
from azul.logging import get_logger

log = get_logger(__name__)

OVERSAMPLE = 3  # fetch ~3x n raw candidates; scoring/dedup thin the herd later
_MAX_QUERIES = 8
_RESULTS_PER_SEARCH = 8
_EXTRACTS_PER_QUERY = 2
_CONTENT_BUDGET = 6000  # chars of page content fed to the extraction LLM

_QUERY_SYSTEM = """\
You generate web-search queries to FIND COMPANIES matching an ICP (ideal
customer profile). Favour queries that surface LISTS: directories, rankings,
"top X", sector associations, award lists, marketplaces — in the ICP's language
and geography. Return STRICT JSON: {"queries": ["...", ...]} (max %d, diverse).
"""

_EXTRACT_SYSTEM = """\
You mine raw web-page text for companies that could match an ICP.
For each company found, return: company_name, domain (bare domain like
"acme.fr" — from an explicit URL or a confident guess; "" if unknown),
founder_name (if present in the text, else ""), founder_role (e.g. "CEO",
"fondateur"; "" if unknown). Only companies plausibly matching the ICP.
Return STRICT JSON: {"candidates": [{"company_name": str, "domain": str,
"founder_name": str, "founder_role": str}, ...]}.
"""

_DOMAIN_RE = re.compile(r"^(?:https?://)?(?:www\.)?([a-z0-9.-]+\.[a-z]{2,})", re.IGNORECASE)


def _clean_domain(value: str) -> str | None:
    m = _DOMAIN_RE.match(value.strip().lower())
    return m.group(1) if m else None


def fallback_queries(brief: ICPBrief) -> list[str]:
    """Deterministic queries when the LLM is unavailable — never block discovery."""
    base = " ".join(filter(None, [brief.sector, brief.geo]))
    return [
        f"annuaire {base}",
        f"top {base}",
        f"liste {base} {brief.company_size}".strip(),
        f"classement {base}",
    ]


class WebDiscovery(CandidateDiscovery):
    name: ClassVar[str] = "web"

    def __init__(self, timeout: float = 30.0) -> None:
        s = get_settings()
        if not s.tavily_api_key:
            raise ConfigError("TAVILY_API_KEY is required for web discovery")
        self._max_calls = s.discovery_max_searches
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

    def _search(self, query: str) -> list[dict[str, Any]]:
        data = self._post(
            "/search",
            {"query": query, "search_depth": "basic", "max_results": _RESULTS_PER_SEARCH},
        )
        return list(data.get("results") or [])

    def _extract(self, urls: list[str]) -> list[dict[str, Any]]:
        data = self._post("/extract", {"urls": urls})
        return list(data.get("results") or [])

    def _gen_queries(self, brief: ICPBrief) -> list[str]:
        try:
            data = chat_json(
                [
                    {"role": "system", "content": _QUERY_SYSTEM % _MAX_QUERIES},
                    {"role": "user", "content": brief.as_prompt_context()},
                ]
            )
            queries = [str(q) for q in (data.get("queries") or []) if str(q).strip()]
        except LLMError as exc:
            log.warning("discovery_query_gen_failed", error=str(exc))
            queries = []
        return (queries or fallback_queries(brief))[:_MAX_QUERIES]

    def _mine(
        self, content: str, source_url: str | None, brief: ICPBrief
    ) -> list[ProspectCandidate]:
        try:
            data = chat_json(
                [
                    {"role": "system", "content": _EXTRACT_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"ICP: {brief.as_prompt_context()}\n\n"
                            f"PAGE ({source_url or 'unknown'}):\n{content[:_CONTENT_BUDGET]}"
                        ),
                    },
                ]
            )
        except LLMError as exc:
            log.warning("discovery_extract_failed", url=source_url, error=str(exc))
            return []
        out: list[ProspectCandidate] = []
        for item in data.get("candidates") or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("company_name") or "").strip()
            domain = _clean_domain(str(item.get("domain") or ""))
            if not name or not domain:
                continue  # no domain = nothing to dedupe or find an email on
            out.append(
                ProspectCandidate(
                    company_name=name,
                    domain=domain,
                    founder_name=str(item.get("founder_name") or "").strip() or None,
                    founder_role=str(item.get("founder_role") or "").strip() or None,
                    source_url=source_url,
                    raw_context=" ".join(content[:400].split()),
                )
            )
        return out

    def discover(self, brief: ICPBrief, n: int) -> list[ProspectCandidate]:
        target = OVERSAMPLE * n
        calls = 0
        seen: set[str] = set()
        out: list[ProspectCandidate] = []

        def take(cands: list[ProspectCandidate]) -> None:
            for c in cands:
                if c.domain not in seen:
                    seen.add(c.domain)
                    out.append(c)

        try:
            for query in self._gen_queries(brief):
                if calls >= self._max_calls or len(out) >= target:
                    break
                results = self._search(query)
                calls += 1
                # Mine the search snippets themselves (one cheap LLM pass per query).
                snippets = "\n\n".join(
                    f"{r.get('url')}\n{r.get('content') or ''}" for r in results
                )
                if snippets.strip():
                    take(self._mine(snippets, f"search:{query}", brief))
                # Extract the top list-looking pages for the long tail.
                urls = [str(r["url"]) for r in results[:_EXTRACTS_PER_QUERY] if r.get("url")]
                if urls and calls < self._max_calls and len(out) < target:
                    pages = self._extract(urls)
                    calls += 1
                    for page in pages:
                        raw = str(page.get("raw_content") or "")
                        if raw.strip():
                            take(self._mine(raw, str(page.get("url") or ""), brief))
        except httpx.HTTPError as exc:
            if not out:
                raise SourcingError(f"Web discovery failed: {exc}") from exc
            log.warning("discovery_partial", error=str(exc), found=len(out))

        log.info("discovery_done", candidates=len(out), tavily_calls=calls, target=target)
        return out[:target]
