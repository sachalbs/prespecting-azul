"""Flywheel: curator + eval. Mines episodic outcomes into procedural skills.

The loop: outcomes -> curate (segment x angle x channel -> win_rate) -> eval
(Wilson lower bound, so tiny samples aren't over-trusted = anti-drift to slop)
-> store as `skills` -> injected back into the Writer. Patterns live at the
SEGMENT level (de-identified) — never per-lead, never cross-tenant leakage.
"""

from __future__ import annotations

import math
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from azul.db.models import Message, Skill
from azul.enums import Channel, MessageStatus
from azul.logging import get_logger

log = get_logger(__name__)


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float:
    """Lower bound of the Wilson score interval — a confidence-adjusted win rate."""
    if n <= 0:
        return 0.0
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return max(0.0, (centre - margin) / denom)


def run_curator(session: Session, *, tenant_id: uuid.UUID | None = None) -> int:
    """Recompute procedural skills from sent touches + their outcomes."""
    stmt = select(Message).where(Message.status == MessageStatus.SENT)
    if tenant_id is not None:
        stmt = stmt.where(Message.tenant_id == tenant_id)

    agg: dict[tuple[str, str, Channel], list[int]] = defaultdict(lambda: [0, 0])
    for m in session.scalars(stmt):
        segment = m.prospect.segment or "unknown"
        key = (segment, m.angle or "none", m.channel)
        agg[key][0] += 1
        if any(o.replied for o in m.outcomes):
            agg[key][1] += 1

    count = 0
    for (segment, angle, channel), (sent, replied) in agg.items():
        skill = session.scalars(
            select(Skill).where(
                Skill.segment == segment,
                Skill.pattern == angle,
                Skill.channel == channel,
                Skill.tenant_id.is_(None),
            )
        ).first()
        if skill is None:
            skill = Skill(segment=segment, pattern=angle, channel=channel)
            session.add(skill)
        skill.sample_size = sent
        skill.win_rate = replied / sent if sent else 0.0
        skill.eval_score = wilson_lower_bound(replied, sent)
        count += 1

    session.flush()
    log.info("curator_ran", patterns=count)
    return count
