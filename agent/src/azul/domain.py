"""Plain DTOs shared across modules — decoupled from the ORM so adapters stay clean."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ProspectBrief:
    """The minimal prospect view an engine needs. No ORM coupling."""

    email: str
    full_name: str | None = None
    title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    segment: str | None = None
    signals: Mapping[str, Any] = field(default_factory=dict)

    @property
    def first_name(self) -> str | None:
        return self.full_name.split()[0] if self.full_name else None
