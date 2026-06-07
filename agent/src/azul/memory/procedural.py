"""Procedural memory: winning patterns by segment (skills).

STUB for Jalon 0. The schema (`skills`, pgvector) is in place so this slots in
without a rewrite, but it's not wired into the Writer yet — we don't synthesise
patterns before we have real outcome data (anti-premature-flywheel).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from azul.db.models import Skill
from azul.enums import Channel


class ProceduralMemory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def skills_for_segment(self, segment: str, channel: Channel | None = None) -> list[Skill]:
        # Intentionally empty in Jalon 0. Later: vector + win_rate ranked retrieval.
        return []

    def hint_for(self, segment: str, channel: Channel | None = None) -> str | None:
        """A short procedural hint to inject into the Writer prompt. None until learned."""
        return None
