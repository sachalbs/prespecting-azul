"""Hook strength scoring — pick the strongest signal, never force a weak one.

On the real run the writer would grab an insignificant detail ("your site has a
non-optimised alt tag") and bend a shaky bridge to the offer. The fix is upstream,
in hook SELECTION: each hook is scored 0-1 by DeepSeek on three criteria —
freshness (a dated/recent event beats a permanent fact beats a minor technical
detail), specificity (true of THIS prospect vs any company in the sector), and
relevance to the offer. A minor technical detail (SEO/alt/typo) is additionally
capped low deterministically, so it can never become the lead hook. If no hook
clears HOOK_MIN_SCORE the caller is told to use a sober angle, not invent a link.
"""

from __future__ import annotations

import re

from azul.errors import AzulError
from azul.llm import chat_json
from azul.logging import get_logger
from azul.research.base import Hook

log = get_logger(__name__)

_BATCH = 12
# A minor technical detail is never a strong hook (item 3) — capped here.
_MINOR_TECHNICAL_CAP = 0.3
_MINOR_TECHNICAL = re.compile(
    r"\b("
    r"balise[s]?\s+(alt|title|meta)|alt\s*tag|alt\s+non|meta[\s-]?description|title\s+tag|"
    r"seo|référencement|typo|faute[s]?\s+d['e]?orthographe|coquille|favicon|sitemap|"
    r"robots\.txt|lien[s]?\s+cass[ée]s?|broken\s+link|erreur\s+404|404|h1\s+manquant|"
    r"balise\s+h1|temps\s+de\s+chargement\s+(d['e]\s*)?une?\s+image"
    r")\b",
    re.IGNORECASE,
)

_SYSTEM = """\
You score outreach hooks for STRENGTH. For EACH hook, rate three axes 0-1:
- freshness: a dated/recent EVENT (hiring, post, funding, launch) = high; a
  permanent fact (description, slogan) = medium; a minor technical detail
  (alt tag, typo, SEO nit) = low.
- specificity: true of THIS prospect specifically vs any company in the sector.
- relevance: does it lead naturally to the problem the offer solves?
Return STRICT JSON: {"scores": [{"index": int, "freshness": float,
"specificity": float, "relevance": float, "reason": str}, ...]} — one per index,
reason in one short clause.
"""


def is_minor_technical(text: str) -> bool:
    return bool(_MINOR_TECHNICAL.search(text or ""))


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _combine(freshness: float, specificity: float, relevance: float) -> float:
    return _clamp(0.4 * freshness + 0.3 * specificity + 0.3 * relevance)


def _apply_cap(hook: Hook) -> None:
    """Minor technical details can never be a strong (lead) hook."""
    if is_minor_technical(hook.text):
        capped = min(hook.strength if hook.strength is not None else _MINOR_TECHNICAL_CAP,
                     _MINOR_TECHNICAL_CAP)
        hook.strength = capped
        hook.strength_reason = (hook.strength_reason or "") + " [minor technical detail, capped]"


def _score_batch(hooks: list[Hook], offer: str, prospect_label: str, offset: int) -> None:
    payload = [{"index": offset + i, "hook": h.text} for i, h in enumerate(hooks)]
    import json

    data = chat_json(
        [
            {"role": "system", "content": _SYSTEM},
            {
                "role": "user",
                "content": (
                    f"Offer: {offer or '-'}\nProspect: {prospect_label or '-'}\n\n"
                    f"HOOKS: {json.dumps(payload, ensure_ascii=False)}"
                ),
            },
        ]
    )
    by_index: dict[int, dict[str, object]] = {}
    for item in data.get("scores") or []:
        if isinstance(item, dict) and isinstance(item.get("index"), int):
            by_index[int(item["index"])] = item
    for i, hook in enumerate(hooks):
        item = by_index.get(offset + i)
        if item is None:
            continue
        try:
            hook.strength = _combine(
                float(item.get("freshness", 0.0)),  # type: ignore[arg-type]
                float(item.get("specificity", 0.0)),  # type: ignore[arg-type]
                float(item.get("relevance", 0.0)),  # type: ignore[arg-type]
            )
        except (TypeError, ValueError):
            hook.strength = None
        hook.strength_reason = str(item.get("reason") or "").strip() or None


def score_hooks(
    hooks: list[Hook], *, offer: str | None = None, prospect_label: str | None = None
) -> list[Hook]:
    """Annotate every hook with a strength + reason (same list back). Drops nothing.

    Uses DeepSeek when configured; otherwise falls back to the relevance proxy
    already on the hook (confidence). The minor-technical cap always applies.
    """
    from azul.config import get_settings

    s = get_settings()
    llm_ready = bool(s.writer_base_url and s.writer_api_key and s.writer_model)
    if hooks and llm_ready:
        for offset in range(0, len(hooks), _BATCH):
            try:
                _score_batch(hooks[offset : offset + _BATCH], offer or "", prospect_label or "",
                             offset)
            except AzulError as exc:
                log.warning("hook_scoring_failed", offset=offset, error=str(exc))
    for hook in hooks:
        if hook.strength is None:
            # No LLM verdict — use confidence as a conservative proxy.
            hook.strength = hook.confidence
            if hook.strength_reason is None:
                hook.strength_reason = "no scorer (confidence proxy)"
        _apply_cap(hook)
    log.info(
        "hooks_scored",
        count=len(hooks),
        scored=sum(1 for h in hooks if h.strength is not None),
    )
    return hooks


def strongest(hooks: list[Hook]) -> Hook | None:
    return max(hooks, key=lambda h: h.strength or 0.0) if hooks else None


def select_hook(hooks: list[Hook], min_score: float) -> tuple[str | None, bool, Hook | None]:
    """(hook_text, weak_hook, chosen). When the best is below min_score, don't force:
    return (None, True, None) so the writer falls back to a sober angle."""
    best = strongest(hooks)
    if best is None or (best.strength or 0.0) < min_score:
        return None, True, None
    return best.text, False, best
