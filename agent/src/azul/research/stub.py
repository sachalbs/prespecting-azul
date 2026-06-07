"""Deterministic stub research — lets the whole loop run and emit a number today.

Produces a plausible hook from the prospect's own signals so the writer has real
material to personalise on. Swap for Holo3 by setting RESEARCH_ENGINE=holo3.
"""

from __future__ import annotations

from typing import ClassVar

from azul.domain import ProspectBrief
from azul.research.base import Hook, ResearchEngine, ResearchResult


class StubResearchEngine(ResearchEngine):
    name: ClassVar[str] = "stub"

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        signals = dict(prospect.signals)
        company = prospect.company or "their company"

        hooks: list[Hook] = []
        if signals:
            key, value = next(iter(signals.items()))
            hooks.append(
                Hook(
                    text=f"{company} — {key.replace('_', ' ')}: {value}",
                    rationale=f"Derived from provided signal '{key}'.",
                    source_url=None,
                    confidence=0.6,
                )
            )
        if prospect.title:
            hooks.append(
                Hook(
                    text=f"As {prospect.title} at {company}, likely owns the related outcome.",
                    rationale="Role-based inference.",
                    confidence=0.4,
                )
            )
        if not hooks:
            hooks.append(Hook(text=f"Generic outreach context for {company}.", confidence=0.2))

        return ResearchResult(
            engine=self.name,
            hooks=hooks,
            sources=[{"type": "stub", "note": "deterministic; no external calls"}],
            raw={"signals": signals},
        )
