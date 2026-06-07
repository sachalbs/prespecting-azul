"""Holo3 adapter (real). Behind `ResearchEngine`, so it's swappable for Qwen3-VL etc.

NOTE: the exact request/response shape is sketched against a conventional REST
contract and must be reconciled with the Holo3 API docs before going live
(search for "TODO(holo3-docs)"). Until then, RESEARCH_ENGINE=stub keeps the
loop running.
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


class Holo3ResearchEngine(ResearchEngine):
    name: ClassVar[str] = "holo3"

    def __init__(self, timeout: float = 60.0) -> None:
        settings = get_settings()
        if not settings.holo3_api_key:
            raise ConfigError("HOLO3_API_KEY is required for RESEARCH_ENGINE=holo3")
        self._base_url = settings.holo3_base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {settings.holo3_api_key}"},
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
        return resp.json()

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        # TODO(holo3-docs): confirm endpoint + payload + response schema.
        payload: dict[str, Any] = {
            "person": {
                "name": prospect.full_name,
                "email": prospect.email,
                "title": prospect.title,
                "company": prospect.company,
                "company_domain": prospect.company_domain,
            },
            "objective": "Find one specific, recent, personalisation-grade hook.",
            "signals": dict(prospect.signals),
        }
        try:
            data = self._post("/v1/research", payload)
        except httpx.HTTPError as exc:
            log.error("holo3_research_failed", email=prospect.email, error=str(exc))
            raise ResearchError(f"Holo3 research failed: {exc}") from exc

        hooks = [
            Hook(
                text=h.get("text", ""),
                rationale=h.get("rationale"),
                source_url=h.get("source_url"),
                confidence=h.get("confidence"),
            )
            for h in data.get("hooks", [])
            if h.get("text")
        ]
        return ResearchResult(
            engine=self.name,
            hooks=hooks,
            sources=data.get("sources", []),
            raw=data,
        )
