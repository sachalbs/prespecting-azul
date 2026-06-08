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
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from azul.config import get_settings
from azul.connectors import OutboundMessage, get_channel
from azul.db.models import (
    Campaign,
    CampaignProspect,
    Message,
    Outcome,
    Prospect,
    Research,
    Tenant,
)
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
from azul.errors import AzulError, ChannelError
from azul.logging import get_logger
from azul.memory import EpisodicMemory, ProceduralMemory
from azul.orchestrator.graph import build_pipeline
from azul.writing import DraftRequest, get_writer

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
    tenant = ensure_tenant(session, tenant_slug, tenant_name)
    campaign = Campaign(tenant_id=tenant.id, name=name, status=CampaignStatus.RUNNING)
    session.add(campaign)
    session.flush()

    pipeline = build_pipeline()
    procedural = ProceduralMemory(session)
    episodic = EpisodicMemory(session)

    for row in rows:
        existing = _find_prospect(session, tenant, row)
        state = pipeline.invoke(
            {
                "prospect": _brief_from_row(row),
                "sender_name": sender_name,
                "value_prop": value_prop,
                # Flywheel: what's worked for this segment (procedural memory).
                "procedural_hint": procedural.hint_for(row.segment),
                # Relationship memory: our prior history with this person (episodic).
                "relationship_note": episodic.recall(existing.id) if existing else None,
            }
        )

        email_status = state.get("email_status", EmailStatus.UNKNOWN)
        resolved_email = state.get("resolved_email") or row.email
        if not resolved_email:
            log.info("prospect_skipped", reason="no_email_found", company=row.company)
            continue

        prospect = _upsert_prospect(
            session, tenant, email=resolved_email, row=row, dossier=state.get("dossier") or {}
        )
        prospect.email_status = email_status
        membership = _ensure_membership(session, campaign, prospect)
        if email_status != EmailStatus.VERIFIED:
            membership.status = MembershipStatus.SKIPPED
            log.info("prospect_skipped", email=prospect.email, email_status=email_status)
            continue

        research = state.get("research")
        if research is not None:
            session.add(
                Research(
                    prospect_id=prospect.id,
                    campaign_id=campaign.id,
                    engine=research.engine,
                    top_hook=research.top_hook,
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
        existing = session.scalars(select(Message).where(Message.dedup_key == dedup_key)).first()
        if existing is None:
            session.add(
                Message(
                    tenant_id=tenant.id,
                    prospect_id=prospect.id,
                    campaign_id=campaign.id,
                    step=1,
                    channel=Channel.EMAIL,
                    angle=draft.angle,
                    subject=draft.subject,
                    body=draft.body,
                    status=MessageStatus.DRAFT,
                    dedup_key=dedup_key,
                )
            )
        membership.status = MembershipStatus.DRAFTED
        log.info("draft_ready", email=prospect.email, angle=draft.angle)

    campaign.status = CampaignStatus.AWAITING_APPROVAL
    session.flush()
    return campaign


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
    sent = 0
    for i, m in enumerate(messages):
        if sent >= settings.daily_send_cap:
            log.warning("daily_cap_reached", cap=settings.daily_send_cap)
            break
        if m.external_id:  # idempotent: already sent
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
            continue
        m.external_id = result.external_id
        m.status = MessageStatus.SENT
        m.sent_at = _now()
        _set_membership(session, m, MembershipStatus.SENT)
        sent += 1
        # Pace real sends for deliverability (never spray). Stub sends instantly.
        if settings.channel != "stub" and i < len(messages) - 1:
            time.sleep(
                random.uniform(settings.send_min_delay_seconds, settings.send_max_delay_seconds)
            )
    session.flush()
    log.info("send_complete", campaign_id=str(campaign_id), sent=sent, dry_run=dry_run)
    return sent


# ── follow-up (one relance for non-repliers, as a child message) ───────────


def generate_followups(
    session: Session,
    *,
    campaign_id: uuid.UUID,
    sender_name: str | None = None,
    value_prop: str | None = None,
) -> int:
    """Draft a step-2 follow-up for each sent prospect who hasn't replied/bounced."""
    writer = get_writer()
    step1 = session.scalars(
        select(Message).where(
            Message.campaign_id == campaign_id,
            Message.step == 1,
            Message.status == MessageStatus.SENT,
        )
    ).all()
    created = 0
    for m in step1:
        if any(o.replied or o.bounced for o in m.outcomes):
            continue
        dedup_key = f"{m.tenant_id}:{m.prospect_id}:2"
        if session.scalars(select(Message).where(Message.dedup_key == dedup_key)).first():
            continue  # idempotent
        prospect = m.prospect
        draft = writer.write(
            DraftRequest(
                prospect=_brief_from_prospect(prospect),
                hook=None,
                step=2,
                prior_body=m.final_body,
                sender_name=sender_name,
                value_prop=value_prop,
            )
        )
        session.add(
            Message(
                tenant_id=m.tenant_id,
                prospect_id=prospect.id,
                campaign_id=campaign_id,
                parent_message_id=m.id,
                step=2,
                channel=Channel.EMAIL,
                angle=draft.angle,
                subject=f"Re: {m.subject}" if m.subject else draft.subject,
                body=draft.body,
                status=MessageStatus.DRAFT,
                dedup_key=dedup_key,
            )
        )
        created += 1
    session.flush()
    log.info("followups_drafted", campaign_id=str(campaign_id), count=created)
    return created


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
    campaign: str
    prospects: int
    drafted: int
    sent: int
    failed: int
    replied: int
    bounced: int
    meetings: int
    sentiments: dict[str, int]

    @property
    def reply_rate(self) -> float:
        return self.replied / self.sent if self.sent else 0.0

    @property
    def bounce_rate(self) -> float:
        return self.bounced / self.sent if self.sent else 0.0


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

    sentiments = Counter(
        o.reply_sentiment.value for o in outcomes if o.replied and o.reply_sentiment
    )
    return CampaignReport(
        campaign=campaign.name,
        prospects=len(members),
        drafted=len(messages),
        sent=sum(1 for m in messages if m.status == MessageStatus.SENT),
        failed=sum(1 for m in messages if m.status == MessageStatus.FAILED),
        replied=sum(1 for o in outcomes if o.replied),
        bounced=sum(1 for o in outcomes if o.bounced),
        meetings=sum(1 for o in outcomes if o.meeting_booked),
        sentiments=dict(sentiments),
    )
