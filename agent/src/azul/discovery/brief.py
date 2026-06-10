"""Conversational ICP brief: the user describes, Azul clarifies, a brief comes out.

DeepSeek drives the conversation: ONE clarifying question at a time, bouncing on
the answers (never a form), stopping as soon as it can target — the code enforces
a hard cap (~6 exchanges) and then forces finalisation. The result is a structured
`ICPBrief` plus the user's own words, persisted per tenant: it is also the
tenant's targeting memory.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from azul.db.models import IcpBrief
from azul.llm import chat_json
from azul.logging import get_logger

log = get_logger(__name__)

DEFAULT_MAX_EXCHANGES = 6

_SYSTEM = """\
You are Azul, an SDR being briefed by your boss about who to prospect.
Collect, through natural conversation: what they sell, their ICP (sector,
company size, geography, target role), what a GREAT prospect looks like,
which pain signals to look for, and the tone they want.

Rules:
- Ask ONE clarifying question at a time. Bounce on their answers — never
  walk through a form.
- Stop as soon as you can target precisely. Do NOT over-ask.
- Mirror the user's language (French in, French out).

Reply with STRICT JSON only:
  {"done": false, "question": "<your single next question>"}
or, when you have enough:
  {"done": true, "brief": {"sells": str, "sector": str, "company_size": str,
   "geo": str, "target_role": str, "good_prospect": str,
   "pain_signals": [str, ...], "tone": str}}
"""

_FINALIZE = (
    "That's enough back-and-forth. Finalise NOW: reply with done=true and the "
    "brief JSON, filling every field as best you can from the conversation."
)


@dataclass(frozen=True)
class ICPBrief:
    """Structured targeting brief + the user's original words."""

    sells: str
    sector: str
    company_size: str
    geo: str
    target_role: str
    good_prospect: str
    pain_signals: tuple[str, ...]
    tone: str
    raw_text: str

    def as_prompt_context(self) -> str:
        """Compact JSON view fed to downstream LLM calls (queries, scoring)."""
        return json.dumps(
            {
                "sells": self.sells,
                "sector": self.sector,
                "company_size": self.company_size,
                "geo": self.geo,
                "target_role": self.target_role,
                "good_prospect": self.good_prospect,
                "pain_signals": list(self.pain_signals),
                "tone": self.tone,
            },
            ensure_ascii=False,
        )


def _brief_from(data: dict[str, object], raw_text: str) -> ICPBrief:
    def text(key: str) -> str:
        return str(data.get(key) or "").strip()

    signals = data.get("pain_signals")
    pain = tuple(str(x) for x in signals) if isinstance(signals, list) else ()
    return ICPBrief(
        sells=text("sells"),
        sector=text("sector"),
        company_size=text("company_size"),
        geo=text("geo"),
        target_role=text("target_role"),
        good_prospect=text("good_prospect"),
        pain_signals=pain,
        tone=text("tone"),
        raw_text=raw_text,
    )


@dataclass
class BriefSession:
    """One brief conversation. start() then reply() until done."""

    max_exchanges: int = DEFAULT_MAX_EXCHANGES
    brief: ICPBrief | None = None
    _messages: list[dict[str, str]] = field(default_factory=list)
    _user_lines: list[str] = field(default_factory=list)
    _exchanges: int = 0

    @property
    def done(self) -> bool:
        return self.brief is not None

    def start(self, initial_text: str) -> str | None:
        """Feed the user's opening description; returns the first question (or None)."""
        self._messages = [{"role": "system", "content": _SYSTEM}]
        return self._turn(initial_text)

    def reply(self, answer: str) -> str | None:
        """Feed one user answer; returns the next question, or None when done."""
        if self.done:
            return None
        return self._turn(answer)

    def _turn(self, user_text: str) -> str | None:
        self._user_lines.append(user_text)
        self._messages.append({"role": "user", "content": user_text})
        self._exchanges += 1
        if self._exchanges >= self.max_exchanges:
            # Never over-interrogate: force the model to ship the brief now.
            self._messages.append({"role": "user", "content": _FINALIZE})
        data = chat_json(self._messages)
        if data.get("done") and isinstance(data.get("brief"), dict):
            self.brief = _brief_from(dict(data["brief"]), raw_text="\n".join(self._user_lines))
            log.info("brief_done", exchanges=self._exchanges)
            return None
        question = str(data.get("question") or "").strip()
        if not question:
            # Model neither finished nor asked — treat as done with what we have.
            payload = data.get("brief") if isinstance(data.get("brief"), dict) else {}
            self.brief = _brief_from(dict(payload or {}), raw_text="\n".join(self._user_lines))
            return None
        self._messages.append({"role": "assistant", "content": json.dumps(data)})
        return question


def save_brief(session: Session, tenant_id: uuid.UUID, brief: ICPBrief) -> IcpBrief:
    """Persist the brief — it is the tenant's reusable targeting memory."""
    row = IcpBrief(
        tenant_id=tenant_id,
        raw_text=brief.raw_text,
        sells=brief.sells,
        sector=brief.sector,
        company_size=brief.company_size,
        geo=brief.geo,
        target_role=brief.target_role,
        good_prospect=brief.good_prospect,
        pain_signals=list(brief.pain_signals),
        tone=brief.tone,
    )
    session.add(row)
    session.flush()
    return row


def load_latest_brief(session: Session, tenant_id: uuid.UUID) -> ICPBrief | None:
    """The tenant's most recent brief, rehydrated (targeting memory reuse)."""
    from sqlalchemy import select

    row = session.scalars(
        select(IcpBrief)
        .where(IcpBrief.tenant_id == tenant_id)
        .order_by(IcpBrief.created_at.desc())
    ).first()
    if row is None:
        return None
    return ICPBrief(
        sells=row.sells or "",
        sector=row.sector or "",
        company_size=row.company_size or "",
        geo=row.geo or "",
        target_role=row.target_role or "",
        good_prospect=row.good_prospect or "",
        pain_signals=tuple(row.pain_signals or []),
        tone=row.tone or "",
        raw_text=row.raw_text,
    )
