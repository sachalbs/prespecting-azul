"""`ResearchEngine` — the contract every research backend (Holo3, Qwen3-VL, …) honours."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from azul.domain import ProspectBrief


@dataclass
class Hook:
    """One concrete, personalisation-grade angle found about a prospect."""

    text: str
    rationale: str | None = None
    source_url: str | None = None
    confidence: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "rationale": self.rationale,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


@dataclass
class ResearchResult:
    engine: str
    hooks: list[Hook] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def top_hook(self) -> str | None:
        if not self.hooks:
            return None
        return max(self.hooks, key=lambda h: h.confidence or 0.0).text


class ResearchEngine(ABC):
    """A commodity behind an interface. The moat is the outcome data, not this."""

    name: ClassVar[str]

    @abstractmethod
    def research(self, prospect: ProspectBrief) -> ResearchResult:
        """Run deep research and return at least one hook (or none if nothing found)."""
        raise NotImplementedError
