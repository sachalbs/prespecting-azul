"""Tiered router: Tavily first, Holo only when tier 1 is poor; tier is logged."""

from __future__ import annotations

from typing import ClassVar

import pytest

from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError
from azul.research.base import Hook, ResearchEngine, ResearchResult
from azul.research.router import TIER1, TIER2, TieredResearchEngine

_P = ProspectBrief(email="ann@acme.com", full_name="Ann Lee", company="Acme")


class FakeEngine(ResearchEngine):
    name: ClassVar[str] = "fake"

    def __init__(self, hooks: list[Hook], error: Exception | None = None) -> None:
        self.hooks = hooks
        self.error = error
        self.calls = 0

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return ResearchResult(engine=self.name, hooks=list(self.hooks))


def _rich() -> list[Hook]:
    return [Hook(text="h1", confidence=0.8), Hook(text="h2", confidence=0.65)]


def _poor() -> list[Hook]:
    return [Hook(text="weak", confidence=0.3)]


def test_rich_tier1_stops_without_holo() -> None:
    t1, t2 = FakeEngine(_rich()), FakeEngine([Hook(text="deep", confidence=0.9)])
    result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
    assert result.tier == TIER1
    assert t2.calls == 0


def test_poor_tier1_escalates_to_holo() -> None:
    t1, t2 = FakeEngine(_poor()), FakeEngine([Hook(text="deep", confidence=0.9)])
    result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
    assert result.tier == TIER2
    assert result.top_hook == "deep"
    assert t1.calls == 1 and t2.calls == 1


def test_tier2_failure_falls_back_to_tier1_result() -> None:
    t1 = FakeEngine(_poor())
    t2 = FakeEngine([], error=ResearchError("browser exploded"))
    result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
    assert result.tier == TIER1
    assert result.top_hook == "weak"


def test_tier2_empty_hooks_keeps_tier1() -> None:
    t1, t2 = FakeEngine(_poor()), FakeEngine([])
    result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
    assert result.tier == TIER1


def test_tier1_failure_still_escalates() -> None:
    t1 = FakeEngine([], error=ResearchError("tavily 429"))
    t2 = FakeEngine([Hook(text="deep", confidence=0.9)])
    result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
    assert result.tier == TIER2


def test_holo_unconfigured_returns_tier1(monkeypatch: pytest.MonkeyPatch) -> None:
    router = TieredResearchEngine(tier1=FakeEngine(_poor()), tier2=None)

    def boom() -> ResearchEngine:
        raise ConfigError("HAI_API_KEY missing")

    monkeypatch.setattr(router, "_tier2_engine", boom)
    result = router.research(_P)
    assert result.tier == TIER1


def test_threshold_comes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from azul.config import get_settings

    monkeypatch.setenv("RESEARCH_TIER_THRESHOLD", "0.9")
    get_settings.cache_clear()
    try:
        # 0.8/0.65 hooks are now below the bar -> escalate.
        t1, t2 = FakeEngine(_rich()), FakeEngine([Hook(text="deep", confidence=0.95)])
        result = TieredResearchEngine(tier1=t1, tier2=t2).research(_P)
        assert result.tier == TIER2
    finally:
        get_settings.cache_clear()


def test_tier_persisted_on_research_row(
    tmp_path: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pathlib import Path

    from sqlalchemy import select

    from azul.db.models import Research
    from azul.db.session import session_scope
    from azul.orchestrator import campaign as camp
    from azul.orchestrator.graph import build_pipeline

    router = TieredResearchEngine(tier1=FakeEngine(_rich()), tier2=FakeEngine([]))
    pipeline = build_pipeline(research_engine=router)
    monkeypatch.setattr(camp, "build_pipeline", lambda: pipeline)

    assert isinstance(tmp_path, Path)
    p = tmp_path / "p.csv"
    p.write_text("email,full_name,company\nann@acme.com,Ann Lee,Acme\n", encoding="utf-8")
    with session_scope() as s:
        camp.run_campaign(s, tenant_slug="t1", name="Q1", rows=camp.load_prospects_csv(str(p)))
    with session_scope() as s:
        row = s.scalars(select(Research)).one()
        assert row.tier == TIER1
        assert row.engine == "fake"
