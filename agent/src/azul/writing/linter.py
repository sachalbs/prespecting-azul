"""Deterministic style linter — the anti-slop gate after every generation.

Rules live in style_rules.yaml (STYLE_RULES_PATH), with safe built-in defaults:
forbidden patterns (em dashes, French filler, AI-tell words), a word budget and
a question budget. A failing draft is regenerated with the offending patterns
as a negative instruction (max 2 attempts); if it still fails it ships flagged
`review_required` so the human knows to look twice.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import yaml

from azul.config import get_settings
from azul.logging import get_logger
from azul.writing.base import Draft, DraftRequest, Writer

log = get_logger(__name__)

_MAX_REGENERATIONS = 2

DEFAULT_FORBIDDEN = [
    "—",  # em dash — the AI tell
    "j'espère que vous allez bien",
    "je me permets",
    "je reviens vers vous",
    "n'hésitez pas",
    "révolutionner",
    "naviguer",
    "paysage",
    "synergie",
]
DEFAULT_MAX_WORDS = 120
DEFAULT_MAX_QUESTIONS = 1


@dataclass(frozen=True)
class StyleRules:
    forbidden_patterns: tuple[str, ...]
    max_words: int
    max_questions: int


@lru_cache(maxsize=4)
def load_rules(path: str) -> StyleRules:
    p = Path(path)
    if not p.exists():
        return StyleRules(tuple(DEFAULT_FORBIDDEN), DEFAULT_MAX_WORDS, DEFAULT_MAX_QUESTIONS)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return StyleRules(
        forbidden_patterns=tuple(
            str(x) for x in (data.get("forbidden_patterns") or DEFAULT_FORBIDDEN)
        ),
        max_words=int(data.get("max_words", DEFAULT_MAX_WORDS)),
        max_questions=int(data.get("max_questions", DEFAULT_MAX_QUESTIONS)),
    )


def get_rules() -> StyleRules:
    return load_rules(get_settings().style_rules_path)


def lint(body: str, rules: StyleRules | None = None) -> list[str]:
    """Human-readable violations, empty when the draft passes."""
    rules = rules or get_rules()
    violations: list[str] = []
    lowered = body.lower()
    for pattern in rules.forbidden_patterns:
        if pattern.lower() in lowered:
            violations.append(f'forbidden pattern "{pattern}"')
    words = len(body.split())
    if words > rules.max_words:
        violations.append(f"{words} words (max {rules.max_words})")
    questions = body.count("?")
    if questions > rules.max_questions:
        violations.append(f"{questions} questions (max {rules.max_questions})")
    return violations


def lint_draft(writer: Writer, request: DraftRequest, rules: StyleRules | None = None) -> Draft:
    """Write, lint, regenerate on failure (max 2), flag review_required if hopeless."""
    rules = rules or get_rules()
    draft = writer.write(request)
    violations = lint(draft.body, rules)
    attempts = 0
    while violations and attempts < _MAX_REGENERATIONS:
        attempts += 1
        log.info(
            "draft_relinted", email=request.prospect.email, attempt=attempts,
            violations=violations,
        )
        feedback = (
            "Your previous draft broke these style rules: "
            + "; ".join(violations)
            + ". Rewrite the message WITHOUT any of these patterns."
        )
        draft = writer.write(replace(request, lint_feedback=feedback))
        violations = lint(draft.body, rules)
    if violations:
        draft.review_required = True
        log.warning(
            "draft_review_required", email=request.prospect.email, violations=violations
        )
    return draft
