"""`Discoverer` — turn an ICP brief into candidate leads. Human-approved before spend."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar


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
