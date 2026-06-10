"""Tiered research router: Tavily first, Holo (browser) only when tier 1 is poor.

"Poor" = fewer than 2 hooks at or above RESEARCH_TIER_THRESHOLD (default 0.6).
The retained tier is stamped on the result (-> `research.tier` column) so the
real Tier1/Tier2 ratio is measurable from day one. If Holo isn't configured or
fails, the tier-1 result ships rather than losing the prospect.
"""

from __future__ import annotations

from typing import ClassVar

from azul.config import get_settings
from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError
from azul.logging import get_logger
from azul.research.base import ResearchEngine, ResearchResult

log = get_logger(__name__)

TIER1 = "tier1"
TIER2 = "tier2"
_MIN_GOOD_HOOKS = 2


class TieredResearchEngine(ResearchEngine):
    name: ClassVar[str] = "tiered"

    def __init__(
        self, tier1: ResearchEngine | None = None, tier2: ResearchEngine | None = None
    ) -> None:
        if tier1 is None:
            from azul.research.tavily import TavilyResearchEngine

            tier1 = TavilyResearchEngine()
        self._tier1 = tier1
        self._tier2 = tier2  # lazy: Holo is only built (and required) on escalation
        self._threshold = get_settings().research_tier_threshold

    def _tier2_engine(self) -> ResearchEngine:
        if self._tier2 is None:
            from azul.research.holo3 import Holo3ResearchEngine

            self._tier2 = Holo3ResearchEngine()
        return self._tier2

    def _is_rich(self, result: ResearchResult) -> bool:
        good = [h for h in result.hooks if (h.confidence or 0.0) >= self._threshold]
        return len(good) >= _MIN_GOOD_HOOKS

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        try:
            t1 = self._tier1.research(prospect)
        except ResearchError as exc:
            log.warning("tier1_failed", email=prospect.email, error=str(exc))
            t1 = ResearchResult(engine=self._tier1.name, hooks=[])

        if self._is_rich(t1):
            t1.tier = TIER1
            log.info("research_tier", email=prospect.email, tier=TIER1, hooks=len(t1.hooks))
            return t1

        try:
            engine2 = self._tier2_engine()
        except ConfigError as exc:
            log.warning("tier2_unavailable", email=prospect.email, error=str(exc))
            t1.tier = TIER1
            return t1
        try:
            t2 = engine2.research(prospect)
        except ResearchError as exc:
            log.warning("tier2_failed", email=prospect.email, error=str(exc))
            t1.tier = TIER1
            return t1

        if t2.hooks:
            t2.tier = TIER2
            log.info("research_tier", email=prospect.email, tier=TIER2, hooks=len(t2.hooks))
            return t2
        t1.tier = TIER1
        log.info("research_tier", email=prospect.email, tier=TIER1, hooks=len(t1.hooks))
        return t1
