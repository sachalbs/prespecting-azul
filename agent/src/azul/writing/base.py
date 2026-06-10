"""`Writer` — the one call where we pay for quality. Swappable text model behind it."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from azul.domain import ProspectBrief
from azul.enums import HookType


@dataclass
class DraftRequest:
    prospect: ProspectBrief
    hook: str | None
    channel: str = "email"
    sender_name: str | None = None
    # One line on who we are / what we offer — kept short on purpose.
    value_prop: str | None = None
    # Follow-ups: step >= 2, with the prior message for light context.
    step: int = 1
    prior_body: str | None = None
    # Procedural memory: what's worked for this segment (a prior, not a script).
    procedural_hint: str | None = None
    # Episodic memory: our prior relationship with THIS person, if any.
    relationship_note: str | None = None


@dataclass
class Draft:
    body: str
    subject: str | None = None
    angle: str | None = None
    # Which taxonomy bucket the hook belongs to (learning log).
    hook_type: HookType | None = None


class Writer(ABC):
    name: ClassVar[str]

    @abstractmethod
    def write(self, request: DraftRequest) -> Draft:
        """Produce one hyper-personalised message. No templates, no slop."""
        raise NotImplementedError
