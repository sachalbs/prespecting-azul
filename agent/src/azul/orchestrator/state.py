"""State carried through the per-prospect LangGraph pipeline."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict

from azul.domain import ProspectBrief
from azul.enums import EmailStatus, VerifyStatus
from azul.research.base import ResearchResult
from azul.writing.base import Draft


class ProspectState(TypedDict):
    prospect: ProspectBrief
    sender_name: NotRequired[str | None]
    value_prop: NotRequired[str | None]
    procedural_hint: NotRequired[str | None]
    relationship_note: NotRequired[str | None]
    # Language inference: the tenant's targeting hint in, the inferred code out.
    language_hint: NotRequired[str | None]
    target_language: NotRequired[str | None]
    # Founder resolution (runs before the finder when no name is known):
    #   "resolved" | "no_founder" | None (skipped because a name was already present)
    resolve_status: NotRequired[str | None]
    resolve_confidence: NotRequired[float | None]
    email_status: NotRequired[EmailStatus]
    verify_status: NotRequired[VerifyStatus | None]
    verify_confidence: NotRequired[float | None]
    resolved_email: NotRequired[str | None]
    dossier: NotRequired[dict[str, Any]]
    research: NotRequired[ResearchResult | None]
    draft: NotRequired[Draft | None]
