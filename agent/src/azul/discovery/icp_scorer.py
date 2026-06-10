"""ICP scoring: every candidate compared to the brief by DeepSeek — annotate, never drop.

Each candidate gets a 0-1 score and a short reason (why it fits the brief or
not). NOTHING is discarded here: the sorted score is decision support, deletion
is the user's decision at selection time. Scoring failures annotate too
(score=None) so the human sees what couldn't be judged.
"""

from __future__ import annotations

import json

from azul.discovery.base import ProspectCandidate
from azul.discovery.brief import ICPBrief
from azul.errors import LLMError
from azul.llm import chat_json
from azul.logging import get_logger

log = get_logger(__name__)

_BATCH = 10

_SYSTEM = """\
You score prospect candidates against an ICP (ideal customer profile).
For EACH candidate, return a fit score between 0 and 1 (1 = textbook match)
and one SHORT reason in the user's language: why it fits the brief, or why not.
Judge only from the provided evidence; uncertainty lowers the score.
Return STRICT JSON: {"scores": [{"index": int, "score": float, "reason": str}, ...]}
with exactly one entry per candidate index.
"""


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_batch(brief: ICPBrief, batch: list[ProspectCandidate], offset: int) -> None:
    payload = [
        {
            "index": offset + i,
            "company": c.company_name,
            "domain": c.domain,
            "founder": c.founder_name,
            "role": c.founder_role,
            "evidence": c.raw_context[:400],
        }
        for i, c in enumerate(batch)
    ]
    data = chat_json(
        [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"ICP: {brief.as_prompt_context()}\n\n"
                    f"CANDIDATES: {json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ]
    )
    by_index: dict[int, dict[str, object]] = {}
    for item in data.get("scores") or []:
        if isinstance(item, dict) and isinstance(item.get("index"), int):
            by_index[int(item["index"])] = item
    for i, candidate in enumerate(batch):
        item = by_index.get(offset + i)
        if item is None:
            continue
        try:
            candidate.icp_score = _clamp(float(item.get("score", 0.0)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            candidate.icp_score = None
        candidate.score_reason = str(item.get("reason") or "").strip() or None


def score_candidates(
    brief: ICPBrief, candidates: list[ProspectCandidate]
) -> list[ProspectCandidate]:
    """Annotate every candidate in place (score + reason); returns the SAME list."""
    for offset in range(0, len(candidates), _BATCH):
        batch = candidates[offset : offset + _BATCH]
        try:
            _score_batch(brief, batch, offset)
        except LLMError as exc:
            log.warning("icp_scoring_failed", offset=offset, error=str(exc))
            for c in batch:
                if c.score_reason is None:
                    c.score_reason = "scoring indisponible (erreur LLM)"
    log.info(
        "icp_scored",
        candidates=len(candidates),
        scored=sum(1 for c in candidates if c.icp_score is not None),
    )
    return candidates


def sorted_by_score(candidates: list[ProspectCandidate]) -> list[ProspectCandidate]:
    """Decision-support order: best fit first, unscored last. Drops nothing."""
    return sorted(
        candidates, key=lambda c: c.icp_score if c.icp_score is not None else -1.0, reverse=True
    )
