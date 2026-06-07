"""State carried through the per-prospect LangGraph pipeline."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from azul.domain import ProspectBrief
from azul.enums import EmailStatus
from azul.research.base import ResearchResult
from azul.writing.base import Draft


class ProspectState(TypedDict):
    prospect: ProspectBrief
    sender_name: NotRequired[str | None]
    value_prop: NotRequired[str | None]
    email_status: NotRequired[EmailStatus]
    research: NotRequired[ResearchResult | None]
    draft: NotRequired[Draft | None]
