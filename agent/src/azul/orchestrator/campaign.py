"""Campaign lifecycle: load -> run (draft) -> approve -> send -> outcomes -> report.

Idempotent throughout: prospects are upserted, messages are dedup-keyed, sends
are guarded by status + external_id so we never double-send.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from azul.config import get_settings
from azul.connectors import OutboundMessage, get_channel
from azul.costs import cost_context
from azul.db.models import (
    Campaign,
    CampaignProspect,
    Message,
    Outcome,
    Prospect,
    Research,
    Tenant,
)
from azul.discovery import get_discoverer
from azul.domain import ProspectBrief
from azul.enums import (
    CampaignStatus,
    Channel,
    EmailStatus,
    MembershipStatus,
    MessageStatus,
    ReplySentiment,
    ReviewDecision,
)
from azul.errors import AzulError, ChannelError, ResearchError, SourcingError, WritingError
from azul.logging import get_logger
from azul.memory import EpisodicMemory, ProceduralMemory
from azul.orchestrator.graph import build_pipeline
from azul.writing import DraftRequest, get_writer
from azul.writing.linter import lint_draft

log = get_logger(__name__)

KNOWN_COLS = {
    "email",
    "full_name",
    "title",
    "company",
    "company_domain",
    "segment",
    "signals",
}


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _as_utc(dt: datetime) -> datetime:
    """sqlite returns naive datetimes; we store UTC, so re-attach it for math."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


# ── CSV loading ─────────────────────────────────────────────────────────────


@dataclass
class CsvRow:
    email: str
    full_name: str | None = None
    title: str | None = None
    company: str | None = None
    company_domain: str | None = None
    segment: str | None = None
    signals: dict[str, object] = field(default_factory=dict)


def load_prospects_csv(path: str) -> list[CsvRow]:
    rows: list[CsvRow] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            clean = {
                (k or "").strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in raw.items()
                if k
            }
            email = clean.get("email")
            # Keep a row if it has an email OR enough to find one (name + domain).
            if not email and not (clean.get("full_name") and clean.get("company_domain")):
                continue
            signals: dict[str, object] = {}
            if clean.get("signals"):
                try:
                    signals = json.loads(str(clean["signals"]))
                except json.JSONDecodeError:
                    signals = {"note": clean["signals"]}
            for key, value in clean.items():
                if key not in KNOWN_COLS and value:
                    signals.setdefault(key, value)
            rows.append(
                CsvRow(
                    email=email or "",
                    full_name=clean.get("full_name") or None,
                    title=clean.get("title") or None,
                    company=clean.get("company") or None,
                    company_domain=clean.get("company_domain") or None,
                    segment=clean.get("segment") or None,
                    signals=signals,
                )
            )
    return rows


# ── helpers ─────────────────────────────────────────────────────────────────


def ensure_tenant(session: Session, slug: str, name: str | None = None) -> Tenant:
    tenant = session.scalars(select(Tenant).where(Tenant.slug == slug)).first()
    if tenant is None:
        tenant = Tenant(slug=slug, name=name or slug)
        session.add(tenant)
        session.flush()
    return tenant


def resolve_campaign(session: Session, ident: str) -> Campaign:
    try:
        cid = uuid.UUID(ident)
    except ValueError:
        campaign = session.scalars(
            select(Campaign).where(Campaign.name == ident).order_by(Campaign.created_at.desc())
        ).first()
    else:
        campaign = session.get(Campaign, cid)
    if campaign is None:
        raise AzulError(f"Campaign not found: {ident}")
    return campaign


def _brief_from_row(row: CsvRow) -> ProspectBrief:
    return ProspectBrief(
        email=row.email or "",
        full_name=row.full_name,
        title=row.title,
        company=row.company,
        company_domain=row.company_domain,
        segment=row.segment,
        signals=dict(row.signals),
    )


def _brief_from_prospect(p: Prospect) -> ProspectBrief:
    return ProspectBrief(
        email=p.email,
        full_name=p.full_name,
        given_name=p.first_name,
        family_name=p.last_name,
        title=p.title,
        company=p.company,
        company_domain=p.company_domain,
        segment=p.segment,
        signals=dict(p.signals or {}),
    )


def _upsert_prospect(
    session: Session,
    tenant: Tenant,
    *,
    email: str,
    row: CsvRow,
    dossier: dict[str, object] | None = None,
) -> Prospect:
    p = session.scalars(
        select(Prospect).where(Prospect.tenant_id == tenant.id, Prospect.email == email)
    ).first()
    if p is None:
        p = Prospect(tenant_id=tenant.id, email=email, source="csv")
        session.add(p)
    p.full_name = row.full_name or p.full_name
    p.title = row.title or p.title
    p.company = row.company or p.company
    p.company_domain = row.company_domain or p.company_domain
    p.segment = row.segment or p.segment
    merged: dict[str, object] = {**(p.signals or {}), **row.signals}
    if dossier:
        merged["dossier"] = dossier
    p.signals = merged
    session.flush()
    return p


def _find_prospect(session: Session, tenant: Tenant, row: CsvRow) -> Prospect | None:
    """Best-effort lookup of an existing prospect (for relationship memory)."""
    if row.email:
        p = session.scalars(
            select(Prospect).where(Prospect.tenant_id == tenant.id, Prospect.email == row.email)
        ).first()
        if p is not None:
            return p
    if row.full_name and row.company_domain:
        return session.scalars(
            select(Prospect).where(
                Prospect.tenant_id == tenant.id,
                Prospect.full_name == row.full_name,
                Prospect.company_domain == row.company_domain,
            )
        ).first()
    return None


def _ensure_membership(
    session: Session, campaign: Campaign, prospect: Prospect
) -> CampaignProspect:
    m = session.scalars(
        select(CampaignProspect).where(
            CampaignProspect.campaign_id == campaign.id,
            CampaignProspect.prospect_id == prospect.id,
        )
    ).first()
    if m is None:
        m = CampaignProspect(campaign_id=campaign.id, prospect_id=prospect.id)
        session.add(m)
        session.flush()
    return m


def _set_membership(session: Session, message: Message, status: MembershipStatus) -> None:
    m = session.scalars(
        select(CampaignProspect).where(
            CampaignProspect.campaign_id == message.campaign_id,
            CampaignProspect.prospect_id == message.prospect_id,
        )
    ).first()
    if m is not None:
        m.status = status


# ── run: source -> research -> write (drafts await human approval) ──────────


def _language_hint(session: Session, tenant: Tenant) -> str | None:
    """The tenant's targeting brief (geo + own words) — feeds language inference."""
    from azul.discovery.brief import load_latest_brief

    brief = load_latest_brief(session, tenant.id)
    if brief is None:
        return None
    return f"geo: {brief.geo or '-'}; sector: {brief.sector or '-'}; {brief.raw_text}"[:600]


def _process_rows(
    session: Session,
    campaign: Campaign,
    tenant: Tenant,
    rows: list[CsvRow],
    *,
    sender_name: str | None,
    value_prop: str | None,
) -> None:
    """Per-prospect pipeline (verify/find email -> research -> write) into drafts."""
    pipeline = build_pipeline()
    procedural = ProceduralMemory(session)
    episodic = EpisodicMemory(session)
    language_hint = _language_hint(session, tenant)
    hook_strengths: list[float] = []

    for row in rows:
        existing = _find_prospect(session, tenant, row)
        try:
            # Cost attribution: the prospect row may not exist yet (research/draft
            # run before the upsert), so attribute by label + campaign.
            with cost_context(
                campaign_id=campaign.id,
                prospect_id=existing.id if existing else None,
                prospect_label=row.email or row.company or row.full_name,
            ):
                state = pipeline.invoke(
                    {
                        "prospect": _brief_from_row(row),
                        "sender_name": sender_name,
                        "value_prop": value_prop,
                        # Flywheel: what's worked for this segment (procedural memory).
                        "procedural_hint": procedural.hint_for(row.segment),
                        # Relationship memory: our prior history with this person (episodic).
                        "relationship_note": episodic.recall(existing.id) if existing else None,
                        # Targeting brief context for per-prospect language inference.
                        "language_hint": language_hint,
                        # Reuse a previously inferred language (skips a redundant LLM call).
                        "target_language": existing.target_language if existing else None,
                    }
                )
        except (SourcingError, ResearchError, WritingError) as exc:
            # One bad prospect must never roll back the whole campaign.
            log.error(
                "prospect_failed", email=row.email or None, company=row.company, error=str(exc)
            )
            failed = existing
            if failed is None and row.email:
                failed = _upsert_prospect(session, tenant, email=row.email, row=row)
            if failed is not None:
                _ensure_membership(session, campaign, failed).status = MembershipStatus.FAILED
            continue

        # No decision-maker found for the company: skip with an explicit, distinct
        # reason (not no_email_found). Persist it so the skip is visible.
        if state.get("resolve_status") == "no_founder":
            placeholder = row.email or (
                f"contact@{row.company_domain}" if row.company_domain else ""
            )
            if placeholder:
                skipped = _upsert_prospect(session, tenant, email=placeholder, row=row)
                _ensure_membership(session, campaign, skipped).status = MembershipStatus.SKIPPED
            log.info("prospect_skipped", reason="no_founder_found", company=row.company)
            continue

        # The resolver may have found a founder the CSV row didn't carry.
        resolved_brief = state.get("prospect")
        resolved_name = resolved_brief.full_name if resolved_brief else None
        resolved_title = resolved_brief.title if resolved_brief else None
        resolved_given = resolved_brief.given_name if resolved_brief else None
        resolved_family = resolved_brief.family_name if resolved_brief else None

        email_status = state.get("email_status", EmailStatus.UNKNOWN)
        resolved_email = state.get("resolved_email") or row.email
        if not resolved_email:
            log.info("prospect_skipped", reason="no_email_found", company=row.company)
            continue

        prospect = _upsert_prospect(
            session, tenant, email=resolved_email, row=row, dossier=state.get("dossier") or {}
        )
        # Persist the resolved decision-maker on the prospect (name parts incl.).
        if resolved_name and not prospect.full_name:
            prospect.full_name = resolved_name
            prospect.title = resolved_title or prospect.title
        if resolved_given and not prospect.first_name:
            prospect.first_name = resolved_given
            prospect.last_name = resolved_family
        # Persist the inferred outreach language once (reused on redraft).
        inferred_language = state.get("target_language")
        if inferred_language and not prospect.target_language:
            prospect.target_language = inferred_language
        prospect.email_status = email_status
        prospect.verify_status = state.get("verify_status")
        prospect.verify_confidence = state.get("verify_confidence")
        membership = _ensure_membership(session, campaign, prospect)
        # Send policy: only a hard INVALID (or a masked address) skips.
        if email_status == EmailStatus.INVALID or "*" in resolved_email:
            membership.status = MembershipStatus.SKIPPED
            log.info("prospect_skipped", email=prospect.email, email_status=email_status)
            continue
        if email_status != EmailStatus.VERIFIED:
            # Catch-all / unknown: allowed but flagged — the human sees it at review.
            log.warning("prospect_flagged", email=prospect.email, email_status=email_status)

        weak_hook = bool(state.get("weak_hook", False))
        research = state.get("research")
        if research is not None:
            hook_strengths.extend(h.strength for h in research.hooks if h.strength is not None)
            session.add(
                Research(
                    prospect_id=prospect.id,
                    campaign_id=campaign.id,
                    engine=research.engine,
                    tier=research.tier,
                    # The selected (strongest above-bar) hook; None when all fell short.
                    top_hook=state.get("selected_hook"),
                    hooks=[h.as_dict() for h in research.hooks],
                    sources=research.sources,
                    raw=research.raw,
                )
            )
            membership.status = MembershipStatus.RESEARCHED

        draft = state.get("draft")
        if draft is None:
            continue

        dedup_key = f"{tenant.id}:{prospect.id}:1"
        existing_msg = session.scalars(
            select(Message).where(Message.dedup_key == dedup_key)
        ).first()
        if existing_msg is None:
            session.add(
                Message(
                    tenant_id=tenant.id,
                    prospect_id=prospect.id,
                    campaign_id=campaign.id,
                    step=1,
                    channel=Channel.EMAIL,
                    angle=draft.angle,
                    hook_type=draft.hook_type,
                    subject_len=len(draft.subject or ""),
                    word_count=len(draft.body.split()),
                    subject=draft.subject,
                    body=draft.body,
                    status=MessageStatus.DRAFT,
                    review_required=draft.review_required,
                    weak_hook=weak_hook,
                    dedup_key=dedup_key,
                )
            )
        membership.status = MembershipStatus.DRAFTED
        log.info("draft_ready", email=prospect.email, angle=draft.angle, weak_hook=weak_hook)

    _log_hook_distribution(campaign, hook_strengths)


def _log_hook_distribution(campaign: Campaign, strengths: list[float]) -> None:
    """Strong/medium/weak hook ratio for the batch — visibility on signal quality."""
    strong = sum(1 for s in strengths if s >= 0.7)
    medium = sum(1 for s in strengths if 0.5 <= s < 0.7)
    weak = sum(1 for s in strengths if s < 0.5)
    log.info(
        "hook_strength_distribution",
        campaign_id=str(campaign.id),
        hooks=len(strengths),
        strong=strong,
        medium=medium,
        weak=weak,
    )


def run_campaign(
    session: Session,
    *,
    tenant_slug: str,
    name: str,
    rows: list[CsvRow],
    tenant_name: str | None = None,
    sender_name: str | None = None,
    value_prop: str | None = None,
) -> Campaign:
    """CSV flow: process a provided list straight to drafts."""
    tenant = ensure_tenant(session, tenant_slug, tenant_name)
    campaign = Campaign(tenant_id=tenant.id, name=name, status=CampaignStatus.RUNNING)
    session.add(campaign)
    session.flush()
    _process_rows(session, campaign, tenant, rows, sender_name=sender_name, value_prop=value_prop)
    campaign.status = CampaignStatus.AWAITING_APPROVAL
    session.flush()
    return campaign


# ── discovery flow: ICP brief -> leads -> (human approves list) -> drafts ────


def discover_campaign(
    session: Session,
    *,
    tenant_slug: str,
    name: str,
    icp_brief: str,
    limit: int = 25,
    tenant_name: str | None = None,
) -> Campaign:
    """Discover candidate leads from an ICP brief; they await human list approval."""
    tenant = ensure_tenant(session, tenant_slug, tenant_name)
    campaign = Campaign(tenant_id=tenant.id, name=name, status=CampaignStatus.DISCOVERED)
    leads = get_discoverer().discover(icp_brief, limit=limit)
    campaign.leads = [lead.as_row() for lead in leads]
    session.add(campaign)
    session.flush()
    log.info("campaign_discovered", campaign_id=str(campaign.id), leads=len(leads))
    return campaign


def list_leads(session: Session, campaign_id: uuid.UUID) -> list[dict[str, object]]:
    campaign = session.get(Campaign, campaign_id)
    return list(campaign.leads) if campaign else []


def approve_list(
    session: Session,
    *,
    campaign_id: uuid.UUID,
    sender_name: str | None = None,
    value_prop: str | None = None,
) -> int:
    """Approve the discovered list -> run the pipeline on it (find email, research, write)."""
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise AzulError(f"Campaign not found: {campaign_id}")
    tenant = session.get(Tenant, campaign.tenant_id)
    if tenant is None:
        raise AzulError("Campaign has no tenant")
    rows = [
        CsvRow(
            email="",
            full_name=lead.get("full_name") or None,
            title=lead.get("title") or None,
            company=lead.get("company") or None,
            company_domain=lead.get("company_domain") or None,
            signals={"source_url": lead["source_url"]} if lead.get("source_url") else {},
        )
        for lead in (campaign.leads or [])
    ]
    campaign.status = CampaignStatus.RUNNING
    _process_rows(session, campaign, tenant, rows, sender_name=sender_name, value_prop=value_prop)
    campaign.status = CampaignStatus.AWAITING_APPROVAL
    session.flush()
    return len(list_drafts(session, campaign_id))


# ── approve (the human tap) ─────────────────────────────────────────────────


def list_drafts(session: Session, campaign_id: uuid.UUID) -> list[Message]:
    return list(
        session.scalars(
            select(Message)
            .where(Message.campaign_id == campaign_id, Message.status == MessageStatus.DRAFT)
            .order_by(Message.created_at)
        )
    )


def approve(
    session: Session,
    *,
    campaign_id: uuid.UUID,
    message_ids: list[uuid.UUID] | None = None,
    approve_all: bool = False,
    approved_by: str = "cli",
) -> int:
    stmt = select(Message).where(
        Message.campaign_id == campaign_id, Message.status == MessageStatus.DRAFT
    )
    if message_ids:
        stmt = stmt.where(Message.id.in_(message_ids))
    elif not approve_all:
        return 0
    messages = list(session.scalars(stmt))
    for m in messages:
        m.status = MessageStatus.APPROVED
        m.review_decision = ReviewDecision.APPROVE
        m.approved_by = approved_by
        m.approved_at = _now()
        _set_membership(session, m, MembershipStatus.APPROVED)
    log.info("approved", campaign_id=str(campaign_id), count=len(messages))
    return len(messages)


# ── send (idempotent, paced) ────────────────────────────────────────────────


def send_approved(session: Session, *, campaign_id: uuid.UUID, dry_run: bool = False) -> int:
    settings = get_settings()
    channel = get_channel()
    campaign = session.get(Campaign, campaign_id)
    if campaign is not None:
        campaign.status = CampaignStatus.SENDING

    messages = list(
        session.scalars(
            select(Message)
            .where(
                Message.campaign_id == campaign_id,
                Message.status == MessageStatus.APPROVED,
            )
            .order_by(Message.created_at)
        )
    )
    # The cap is per DAY, not per invocation: count today's sends across the DB.
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    sent_today: int = (
        session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.status == MessageStatus.SENT, Message.sent_at >= today_start)
        )
        or 0
    )

    # A reply may have landed between approval and send: never follow up a
    # prospect who answered. (First touches are unaffected — you can't reply
    # before any send.)
    replied_prospects = set(
        session.scalars(
            select(Message.prospect_id)
            .join(Outcome, Outcome.message_id == Message.id)
            .where(Message.campaign_id == campaign_id, Outcome.replied.is_(True))
        )
    )

    sent = 0
    for i, m in enumerate(messages):
        if sent_today + sent >= settings.daily_send_cap:
            log.warning(
                "daily_cap_reached", cap=settings.daily_send_cap, sent_today=sent_today + sent
            )
            break
        if m.external_id:  # idempotent: already sent
            continue
        if m.step > 1 and m.prospect_id in replied_prospects:
            m.status = MessageStatus.SKIPPED
            m.error = "cancelled: prospect replied before the follow-up went out"
            log.info("followup_cancelled", to=m.prospect.email, step=m.step)
            session.commit()
            continue
        out = OutboundMessage(
            channel=m.channel,
            body=m.final_body,
            dedup_key=m.dedup_key,
            to_email=m.prospect.email,
            subject=m.subject,
        )
        if dry_run:
            log.info("dry_run_send", to=m.prospect.email, subject=m.subject)
            continue
        try:
            result = channel.send(out)
        except ChannelError as exc:
            m.status = MessageStatus.FAILED
            m.error = str(exc)
            log.error("send_failed", to=m.prospect.email, error=str(exc))
            session.commit()
            continue
        m.external_id = result.external_id
        # Provider thread id (Graph conversationId): lets sync-replies match by thread.
        m.conversation_id = str(result.raw.get("conversationId") or "") or None
        m.status = MessageStatus.SENT
        m.sent_at = _now()
        _set_membership(session, m, MembershipStatus.SENT)
        sent += 1
        # Persist each send immediately: a crash mid-batch must never roll back
        # already-sent statuses, or re-running would double-send real emails.
        session.commit()
        # Pace real sends for deliverability (never spray). Stub sends instantly.
        if settings.channel != "stub" and i < len(messages) - 1:
            time.sleep(
                random.uniform(settings.send_min_delay_seconds, settings.send_max_delay_seconds)
            )
    session.flush()
    log.info("send_complete", campaign_id=str(campaign_id), sent=sent, dry_run=dry_run)
    return sent


# ── redraft (regenerate drafts in place — no resolver/finder/research) ───────


def redraft_campaign(
    session: Session,
    *,
    campaign_id: uuid.UUID,
    sender_name: str | None = None,
    value_prop: str | None = None,
) -> int:
    """Regenerate the step-1 DRAFTs of a campaign from already-persisted data.

    Reuses each prospect's resolved identity, inferred language and stored research
    hook — it never re-runs the resolver, finder or research. Only untouched DRAFTs
    are rewritten; approved/sent messages and human-edited drafts are left alone.
    """
    from azul.research.base import Hook
    from azul.research.hook_scorer import select_hook
    from azul.writing.linter import lint_draft

    writer = get_writer()
    min_score = get_settings().hook_min_score
    drafts = session.scalars(
        select(Message).where(
            Message.campaign_id == campaign_id,
            Message.step == 1,
            Message.status == MessageStatus.DRAFT,
        )
    ).all()
    count = 0
    for m in drafts:
        if m.human_edited_body:
            continue  # never clobber a human's edit
        prospect = m.prospect
        research = session.scalars(
            select(Research)
            .where(Research.prospect_id == prospect.id, Research.campaign_id == campaign_id)
            .order_by(Research.created_at.desc())
        ).first()
        # Reuse the persisted hook scores — no re-scoring, no re-research.
        stored = [Hook(**h) for h in (research.hooks if research else [])]
        selected, weak, _ = select_hook(stored, min_score) if stored else (None, True, None)
        with cost_context(
            campaign_id=campaign_id, prospect_id=prospect.id, prospect_label=prospect.email
        ):
            draft = lint_draft(
                writer,
                DraftRequest(
                    prospect=_brief_from_prospect(prospect),
                    hook=None if weak else selected,
                    sender_name=sender_name,
                    value_prop=value_prop,
                    target_language=prospect.target_language,
                    weak_hook=weak,
                ),
            )
        m.angle = draft.angle
        m.hook_type = draft.hook_type
        m.subject = draft.subject
        m.subject_len = len(draft.subject or "")
        m.word_count = len(draft.body.split())
        m.body = draft.body
        m.review_required = draft.review_required
        m.weak_hook = weak
        count += 1
    session.flush()
    log.info("redrafted", campaign_id=str(campaign_id), count=count)
    return count


# ── follow-ups (relances for non-repliers — drafted, never auto-sent) ───────


def generate_followups(
    session: Session,
    *,
    campaign_id: uuid.UUID,
    sender_name: str | None = None,
    value_prop: str | None = None,
    delay_days: int | None = None,
    max_followups: int | None = None,
    now: datetime | None = None,
) -> int:
    """Draft the next relance for each prospect who is still silent.

    Eligibility (all required):
    - last touch SENT >= FOLLOWUP_DELAY_DAYS ago (env, default 4);
    - no reply and no bounce on ANY touch of this prospect in the campaign;
    - fewer than MAX_FOLLOWUPS relances already (env, default 2).

    The relance is a child Message (parent_message_id + step), goes through the
    writer + linter like any draft, and lands in DRAFT — the human approves it
    via the normal `approve` -> `send-approved` gates. Idempotent per step.
    """
    settings = get_settings()
    delay = timedelta(days=settings.followup_delay_days if delay_days is None else delay_days)
    cap = settings.max_followups if max_followups is None else max_followups
    max_step = 1 + cap  # touches: 1 first email + cap relances
    now = now or _now()
    writer = get_writer()

    # Last SENT touch per prospect (highest step), plus who replied/bounced.
    sent_msgs = session.scalars(
        select(Message)
        .where(Message.campaign_id == campaign_id, Message.status == MessageStatus.SENT)
        .order_by(Message.step)
    ).all()
    last_by_prospect: dict[uuid.UUID, Message] = {}
    for m in sent_msgs:
        last_by_prospect[m.prospect_id] = m  # ordered by step: keeps the highest
    closed_prospects = {
        m.prospect_id
        for m in sent_msgs
        if any(o.replied or o.bounced for o in m.outcomes)
    }

    created = 0
    for prospect_id, last in last_by_prospect.items():
        if prospect_id in closed_prospects:
            continue  # they answered (or bounced): the thread is closed
        if last.step >= max_step:
            continue  # cap reached: stop, no exception
        if last.sent_at is None or now - _as_utc(last.sent_at) < delay:
            continue  # too early: the silence isn't old enough yet
        next_step = last.step + 1
        dedup_key = f"{last.tenant_id}:{prospect_id}:{next_step}"
        if session.scalars(select(Message).where(Message.dedup_key == dedup_key)).first():
            continue  # idempotent: this relance was already drafted
        prospect = last.prospect
        with cost_context(
            campaign_id=campaign_id, prospect_id=prospect.id, prospect_label=prospect.email
        ):
            draft = lint_draft(
                writer,
                DraftRequest(
                    prospect=_brief_from_prospect(prospect),
                    hook=None,
                    step=next_step,
                    prior_body=last.final_body,
                    sender_name=sender_name,
                    value_prop=value_prop,
                    target_language=prospect.target_language,
                ),
            )
        root_subject = last.subject.removeprefix("Re: ") if last.subject else None
        subject = f"Re: {root_subject}" if root_subject else draft.subject
        session.add(
            Message(
                tenant_id=last.tenant_id,
                prospect_id=prospect.id,
                campaign_id=campaign_id,
                parent_message_id=last.id,
                step=next_step,
                channel=Channel.EMAIL,
                angle=draft.angle,
                hook_type=draft.hook_type,
                subject_len=len(subject or ""),
                word_count=len(draft.body.split()),
                subject=subject,
                body=draft.body,
                status=MessageStatus.DRAFT,
                review_required=draft.review_required,
                dedup_key=dedup_key,
            )
        )
        created += 1
    session.flush()
    log.info("followups_drafted", campaign_id=str(campaign_id), count=created)
    return created


def list_followup_drafts(session: Session, campaign_id: uuid.UUID) -> list[Message]:
    """Relance drafts awaiting the human gate (step >= 2, DRAFT)."""
    return list(
        session.scalars(
            select(Message)
            .where(
                Message.campaign_id == campaign_id,
                Message.step > 1,
                Message.status == MessageStatus.DRAFT,
            )
            .order_by(Message.created_at)
        )
    )


# ── simulate replies (stub channel only — populates a real number) ──────────


def simulate_replies(session: Session, *, campaign_id: uuid.UUID) -> int:
    if get_settings().channel != "stub":
        raise AzulError("simulate-replies is only for CHANNEL=stub")
    mem = EpisodicMemory(session)
    messages = list(
        session.scalars(
            select(Message).where(
                Message.campaign_id == campaign_id, Message.status == MessageStatus.SENT
            )
        )
    )
    created = 0
    for m in messages:
        if m.outcomes:  # idempotent
            continue
        h = int(hashlib.sha256(m.prospect.email.encode()).hexdigest(), 16)
        if h % 23 == 0:
            mem.record_outcome(
                message_id=m.id,
                bounced=True,
                bounce_type="hard",
                raw_event={"simulated": True},
            )
        elif h % 4 == 0:
            mem.record_outcome(
                message_id=m.id,
                replied=True,
                reply_sentiment=ReplySentiment.POSITIVE,
                reply_text="Interesting — happy to chat next week.",
                meeting_booked=(h % 8 == 0),
                raw_event={"simulated": True},
            )
            _set_membership(session, m, MembershipStatus.REPLIED)
        elif h % 7 == 0:
            mem.record_outcome(
                message_id=m.id,
                replied=True,
                reply_sentiment=ReplySentiment.NEUTRAL,
                reply_text="Not right now, maybe later.",
                raw_event={"simulated": True},
            )
            _set_membership(session, m, MembershipStatus.REPLIED)
        else:
            continue
        created += 1
    session.flush()
    return created


# ── report (the number that matters: reply rate) ────────────────────────────


@dataclass
class CampaignReport:
    """Reply rate counts UNIQUE PROSPECTS, never emails: with follow-ups one
    prospect receives several touches, but they reply (or not) exactly once."""

    campaign: str
    prospects: int
    drafted: int
    sent: int  # emails that left (touches), informational only
    failed: int
    contacted: int  # unique prospects with >= 1 sent touch — THE denominator
    replied: int  # unique prospects who replied — THE numerator
    bounced: int  # unique prospects that bounced
    meetings: int
    sentiments: dict[str, int]

    @property
    def reply_rate(self) -> float:
        return self.replied / self.contacted if self.contacted else 0.0

    @property
    def bounce_rate(self) -> float:
        return self.bounced / self.contacted if self.contacted else 0.0


def build_report(session: Session, *, campaign_id: uuid.UUID) -> CampaignReport:
    campaign = session.get(Campaign, campaign_id)
    if campaign is None:
        raise AzulError(f"Campaign not found: {campaign_id}")

    members = session.scalars(
        select(CampaignProspect).where(CampaignProspect.campaign_id == campaign_id)
    ).all()
    messages = session.scalars(select(Message).where(Message.campaign_id == campaign_id)).all()
    outcomes = session.scalars(
        select(Outcome).join(Message).where(Message.campaign_id == campaign_id)
    ).all()

    msg_prospect = {m.id: m.prospect_id for m in messages}
    contacted = {m.prospect_id for m in messages if m.status == MessageStatus.SENT}
    replied_prospects = {msg_prospect[o.message_id] for o in outcomes if o.replied}
    bounced_prospects = {msg_prospect[o.message_id] for o in outcomes if o.bounced}
    sentiments = Counter(
        o.reply_sentiment.value for o in outcomes if o.replied and o.reply_sentiment
    )
    return CampaignReport(
        campaign=campaign.name,
        prospects=len(members),
        drafted=len(messages),
        sent=sum(1 for m in messages if m.status == MessageStatus.SENT),
        failed=sum(1 for m in messages if m.status == MessageStatus.FAILED),
        contacted=len(contacted),
        replied=len(replied_prospects),
        bounced=len(bounced_prospects),
        meetings=sum(1 for o in outcomes if o.meeting_booked),
        sentiments=dict(sentiments),
    )
