"""Dossier research — a hook from the Prospeo dossier alone. No browser, no Holo.

This is the v0 ultra-simple research: sourcing (Prospeo enrich) already fetched a
dossier (headline, role, funding, job postings) and stored it on the prospect, so
here we just turn it into 1-3 hooks. Robust, cheap, no LinkedIn scraping, no ban
risk. Holo3 deep-research is the premium upgrade on top, later.
"""

from __future__ import annotations

from typing import Any, ClassVar

from azul.domain import ProspectBrief
from azul.research.base import Hook, ResearchEngine, ResearchResult


class DossierResearchEngine(ResearchEngine):
    name: ClassVar[str] = "dossier"

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        signals = dict(prospect.signals or {})
        dossier: dict[str, Any] = signals.get("dossier") or {}
        company = prospect.company or "their company"
        hooks: list[Hook] = []

        funding = dossier.get("latest_funding")
        if isinstance(funding, dict) and funding.get("stage"):
            amount = funding.get("amount_printed") or "a round"
            hooks.append(
                Hook(
                    text=f"{company} raised {amount} ({funding['stage']}).",
                    rationale="From the latest funding signal.",
                    confidence=0.6,
                )
            )

        jobs = dossier.get("active_job_titles") or []
        if isinstance(jobs, list) and jobs:
            hooks.append(
                Hook(
                    text=f"{company} is hiring ({', '.join(str(j) for j in jobs[:2])}) "
                    "— likely scaling that function.",
                    rationale="From active job postings.",
                    confidence=0.55,
                )
            )

        headline = dossier.get("headline")
        if headline:
            hooks.append(
                Hook(
                    text=f'Their stated focus: "{headline}".',
                    rationale="Headline.",
                    confidence=0.45,
                )
            )

        if not hooks:
            for key, value in signals.items():
                if key != "dossier" and isinstance(value, str) and value:
                    hooks.append(
                        Hook(text=f"{company} — {key.replace('_', ' ')}: {value}", confidence=0.4)
                    )
                    break
        if not hooks and prospect.title:
            hooks.append(
                Hook(text=f"As {prospect.title} at {company}, likely owns this.", confidence=0.3)
            )
        if not hooks:
            hooks.append(Hook(text=f"Outreach context for {company}.", confidence=0.2))

        return ResearchResult(
            engine=self.name,
            hooks=hooks,
            sources=[{"type": "prospeo_dossier"}],
            raw={"dossier": dossier},
        )
