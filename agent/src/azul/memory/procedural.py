"""Procedural memory: winning patterns by segment (skills).

Now live (filled by the flywheel curator). `hint_for` returns the best learned
angle for a segment — injected into the Writer as a prior. A minimum sample guard
keeps us from trusting noise.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from azul.db.models import Skill
from azul.enums import Channel

_MIN_SAMPLE = 3  # don't promote a pattern below this many sends (anti-noise)


class ProceduralMemory:
    def __init__(self, session: Session) -> None:
        self.session = session

    def skills_for_segment(self, segment: str, channel: Channel | None = None) -> list[Skill]:
        stmt = select(Skill).where(Skill.segment == segment).order_by(Skill.eval_score.desc())
        if channel is not None:
            stmt = stmt.where(Skill.channel == channel)
        return list(self.session.scalars(stmt))

    def hint_for(self, segment: str | None, channel: Channel | None = None) -> str | None:
        """A short procedural hint for the Writer prompt. None until something is learned."""
        if not segment:
            return None
        for skill in self.skills_for_segment(segment, channel):
            if skill.sample_size >= _MIN_SAMPLE and (skill.win_rate or 0) > 0:
                return (
                    f"Prior learning for {segment}: the '{skill.pattern}' angle is landing "
                    f"({skill.win_rate:.0%} reply over {skill.sample_size}). "
                    "Use it as a prior, not a script."
                )
        return None
