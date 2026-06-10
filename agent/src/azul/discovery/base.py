"""`Discoverer` — turn an ICP brief into candidate leads. Human-approved before spend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from azul.discovery.brief import ICPBrief


@dataclass
class Lead:
    full_name: str
    company: str | None = None
    company_domain: str | None = None
    title: str | None = None
    source_url: str | None = None

    def as_row(self) -> dict[str, Any]:
        """Shape compatible with the CSV pipeline (a row without an email yet)."""
        return {
            "full_name": self.full_name,
            "company": self.company,
            "company_domain": self.company_domain,
            "title": self.title,
            "source_url": self.source_url,
        }


class Discoverer(ABC):
    name: ClassVar[str]

    @abstractmethod
    def discover(self, icp_brief: str, limit: int = 25) -> list[Lead]:
        """Find up to `limit` leads matching the ICP brief (name + company + domain)."""
        raise NotImplementedError


@dataclass
class ProspectCandidate:
    """One company found during discovery, with its provenance.

    `raw_context` keeps what was actually found (the evidence); `icp_score` and
    `score_reason` are annotations from the ICP scorer — candidates are NEVER
    dropped on score, the human decides.
    """

    company_name: str
    domain: str
    founder_name: str | None = None
    founder_role: str | None = None
    source_url: str | None = None
    raw_context: str = ""
    icp_score: float | None = None
    score_reason: str | None = None

    def as_row(self) -> dict[str, Any]:
        """Shape compatible with the CSV pipeline (a row without an email yet)."""
        return {
            "full_name": self.founder_name,
            "company": self.company_name,
            "company_domain": self.domain,
            "title": self.founder_role,
            "source_url": self.source_url,
        }


class CandidateDiscovery(ABC):
    """Brief-driven discovery: an ICPBrief in, oversampled candidates out."""

    name: ClassVar[str]

    @abstractmethod
    def discover(self, brief: ICPBrief, n: int) -> list[ProspectCandidate]:
        """Find candidates matching the brief (scoring/dedup happen downstream)."""
        raise NotImplementedError
