"""Web-search discoverer (skeleton): ICP brief -> search -> extract leads.

Pipeline (to wire to a real search provider — Brave/Serper/Bing — via SEARCH_API_*):
  1. brief -> a few search queries (LLM),
  2. call the search API,
  3. extract company + person (name / company / domain) from the results (LLM).

TODO(search-provider): implement against the chosen API. Until then this raises
clearly rather than returning junk. Quality here is the weak point without a data
provider (Apollo/Lusha) — see ARCHITECTURE.md §7.3.
"""

from __future__ import annotations

from typing import ClassVar

from azul.config import get_settings
from azul.discovery.base import Discoverer, Lead
from azul.errors import ConfigError, SourcingError


class WebSearchDiscoverer(Discoverer):
    name: ClassVar[str] = "websearch"

    def __init__(self) -> None:
        if not get_settings().search_api_key:
            raise ConfigError("SEARCH_API_KEY required for DISCOVERY_PROVIDER=websearch")

    def discover(self, icp_brief: str, limit: int = 25) -> list[Lead]:
        raise SourcingError(
            "WebSearch discovery is not wired to a search provider yet "
            "(TODO(search-provider) in discovery/websearch.py)"
        )
