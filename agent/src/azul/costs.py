"""API cost tracker: every external call logged with its estimated price.

Goal: know what a prospect costs (to anchor the pricing). Call sites (writer,
chat LLM, Tavily, Holo) record fire-and-forget; attribution comes from the
ambient `cost_context` set by the orchestrator (campaign + prospect). Recording
must never break the pipeline: failures are logged and swallowed.

Prices live in Settings (env-overridable): WRITER_PRICE_IN_PER_MTOK,
WRITER_PRICE_OUT_PER_MTOK, TAVILY_PRICE_PER_CALL, HOLO_PRICE_IN_PER_MTOK,
HOLO_PRICE_OUT_PER_MTOK.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from azul.config import get_settings
from azul.db.models import ApiCall, CampaignProspect, Message
from azul.enums import MessageStatus
from azul.logging import get_logger

log = get_logger(__name__)

_MTOK = 1_000_000


@dataclass(frozen=True)
class CostContext:
    campaign_id: uuid.UUID | None = None
    prospect_id: uuid.UUID | None = None
    prospect_label: str | None = None


_context: ContextVar[CostContext | None] = ContextVar("azul_cost_context", default=None)


@contextmanager
def cost_context(
    *,
    campaign_id: uuid.UUID | None = None,
    prospect_id: uuid.UUID | None = None,
    prospect_label: str | None = None,
) -> Generator[None]:
    """Attribute every API call made inside this block to a campaign/prospect."""
    token = _context.set(
        CostContext(
            campaign_id=campaign_id, prospect_id=prospect_id, prospect_label=prospect_label
        )
    )
    try:
        yield
    finally:
        _context.reset(token)


def _token_prices(service: str) -> tuple[float, float]:
    s = get_settings()
    if service == "holo":
        return s.holo_price_in_per_mtok, s.holo_price_out_per_mtok
    # The writer and the chat helper share the same provider (DeepSeek default).
    return s.writer_price_in_per_mtok, s.writer_price_out_per_mtok


def _persist(row: ApiCall) -> None:
    """Join the caller's open transaction when there is one (sqlite: one writer)."""
    from azul.db.session import active_session, session_scope

    session = active_session()
    if session is not None:
        session.add(row)
        return
    with session_scope() as s:
        s.add(row)


def _record(
    service: str,
    operation: str,
    *,
    calls: int = 1,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
) -> None:
    ctx = _context.get() or CostContext()
    try:
        _persist(
            ApiCall(
                service=service,
                operation=operation,
                campaign_id=ctx.campaign_id,
                prospect_id=ctx.prospect_id,
                prospect_label=ctx.prospect_label,
                calls=calls,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
            )
        )
    except Exception as exc:  # cost tracking must never break the pipeline
        log.warning("api_call_log_failed", service=service, error=str(exc))


def record_llm_usage(service: str, operation: str, usage: dict[str, Any] | None) -> None:
    """Record one chat completion from its `usage` block (deepseek / holo)."""
    usage = usage or {}
    tokens_in = int(usage.get("prompt_tokens") or 0)
    tokens_out = int(usage.get("completion_tokens") or 0)
    price_in, price_out = _token_prices(service)
    cost = (tokens_in * price_in + tokens_out * price_out) / _MTOK
    _record(service, operation, tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost)


def record_call(service: str, operation: str, *, cost_usd: float | None = None) -> None:
    """Record one per-call-priced API hit (Tavily search/extract)."""
    if cost_usd is None:
        cost_usd = get_settings().tavily_price_per_call if service == "tavily" else 0.0
    _record(service, operation, cost_usd=cost_usd)


# ── aggregation (the `azul cost` command) ────────────────────────────────────


@dataclass
class ServiceCost:
    service: str
    calls: int
    tokens_in: int
    tokens_out: int
    cost_usd: float


@dataclass
class CostSummary:
    total_usd: float
    by_service: list[ServiceCost]
    prospects_contacted: int
    attributed_prospects: int

    @property
    def cost_per_contacted_prospect(self) -> float:
        return self.total_usd / self.prospects_contacted if self.prospects_contacted else 0.0


def build_cost_summary(session: Session, *, campaign_id: uuid.UUID) -> CostSummary:
    rows = session.execute(
        select(
            ApiCall.service,
            func.sum(ApiCall.calls),
            func.sum(ApiCall.tokens_in),
            func.sum(ApiCall.tokens_out),
            func.sum(ApiCall.cost_usd),
        )
        .where(ApiCall.campaign_id == campaign_id)
        .group_by(ApiCall.service)
        .order_by(func.sum(ApiCall.cost_usd).desc())
    ).all()
    by_service = [
        ServiceCost(
            service=svc,
            calls=int(calls or 0),
            tokens_in=int(tin or 0),
            tokens_out=int(tout or 0),
            cost_usd=float(cost or 0.0),
        )
        for svc, calls, tin, tout, cost in rows
    ]
    attributed = (
        session.scalar(
            select(func.count(func.distinct(func.coalesce(ApiCall.prospect_label, "?"))))
            .select_from(ApiCall)
            .where(ApiCall.campaign_id == campaign_id, ApiCall.prospect_label.is_not(None))
        )
        or 0
    )
    contacted = (
        session.scalar(
            select(func.count(func.distinct(Message.prospect_id)))
            .select_from(Message)
            .where(
                Message.campaign_id == campaign_id, Message.status == MessageStatus.SENT
            )
        )
        or 0
    )
    # A campaign that never sent still has researched/drafted prospects: fall back
    # to the membership count so cost-per-prospect stays meaningful pre-send.
    if contacted == 0:
        contacted = (
            session.scalar(
                select(func.count())
                .select_from(CampaignProspect)
                .where(CampaignProspect.campaign_id == campaign_id)
            )
            or 0
        )
    return CostSummary(
        total_usd=sum(s.cost_usd for s in by_service),
        by_service=by_service,
        prospects_contacted=contacted,
        attributed_prospects=int(attributed),
    )
