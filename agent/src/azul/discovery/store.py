"""Persist discovery output and promote the human's selection into the pipeline.

Every candidate is saved annotated (audit trail + dedup memory). Promotion is
the explicit human act: selected candidates become Prospect rows (source
"discovery", best-guess email placeholder, never sendable before the pipeline's
verify gate) AND a Campaign in status DISCOVERED whose `leads` feed the existing
`approve_list` entry point — nothing enters the pipeline without this.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from azul.db.models import Campaign, DiscoveryCandidate, Prospect
from azul.discovery.base import ProspectCandidate
from azul.enums import CampaignStatus
from azul.logging import get_logger
from azul.sourcing.finder import candidates as email_candidates

log = get_logger(__name__)


def save_candidates(
    session: Session,
    tenant_id: uuid.UUID,
    candidates: list[ProspectCandidate],
    brief_id: uuid.UUID | None = None,
) -> list[DiscoveryCandidate]:
    """Persist ALL candidates with their annotations — nothing is thrown away."""
    rows = [
        DiscoveryCandidate(
            tenant_id=tenant_id,
            brief_id=brief_id,
            company_name=c.company_name,
            domain=c.domain,
            founder_name=c.founder_name,
            founder_role=c.founder_role,
            source_url=c.source_url,
            raw_context=c.raw_context,
            icp_score=c.icp_score,
            score_reason=c.score_reason,
        )
        for c in candidates
    ]
    session.add_all(rows)
    session.flush()
    return rows


def _placeholder_email(row: DiscoveryCandidate) -> str:
    """Best-guess address in the standard format; the pipeline verifies or replaces it."""
    if row.founder_name:
        guesses = email_candidates(row.founder_name, row.domain)
        if guesses:
            return guesses[0]
    return f"contact@{row.domain}"


def promote(
    session: Session,
    tenant_id: uuid.UUID,
    rows: list[DiscoveryCandidate],
    campaign_name: str,
) -> tuple[list[Prospect], Campaign]:
    """The human's selection: candidates -> Prospects + a DISCOVERED campaign.

    The campaign's `leads` are pipeline rows for the EXISTING approve_list flow
    (find email -> verify -> research -> write), unchanged.
    """
    prospects: list[Prospect] = []
    leads: list[dict[str, object]] = []
    for row in rows:
        prospect = Prospect(
            tenant_id=tenant_id,
            email=_placeholder_email(row),
            full_name=row.founder_name,
            title=row.founder_role,
            company=row.company_name,
            company_domain=row.domain,
            source="discovery",
            signals={
                "source_url": row.source_url,
                "icp_score": row.icp_score,
                "score_reason": row.score_reason,
                "raw_context": row.raw_context,
            },
        )
        session.add(prospect)
        session.flush()
        row.promoted = True
        row.prospect_id = prospect.id
        prospects.append(prospect)
        leads.append(
            {
                "full_name": row.founder_name,
                "company": row.company_name,
                "company_domain": row.domain,
                "title": row.founder_role,
                "source_url": row.source_url,
            }
        )
    campaign = Campaign(
        tenant_id=tenant_id, name=campaign_name, status=CampaignStatus.DISCOVERED, leads=leads
    )
    session.add(campaign)
    session.flush()
    log.info("candidates_promoted", count=len(prospects), campaign_id=str(campaign.id))
    return prospects, campaign


def render_table(rows: list[DiscoveryCandidate]) -> str:
    """Score-sorted decision table: boîte | fondateur | rôle | domaine | score | raison | source."""
    ranked = sorted(
        rows, key=lambda r: r.icp_score if r.icp_score is not None else -1.0, reverse=True
    )

    def cell(value: object, width: int) -> str:
        text = str(value or "-")
        return (text[: width - 1] + "…") if len(text) > width else text.ljust(width)

    header = (
        f"{'#':>3} {cell('boîte', 22)} {cell('fondateur', 18)} {cell('rôle', 12)} "
        f"{cell('domaine', 22)} {'score':>5} {cell('raison', 42)} {cell('source', 30)}"
    )
    lines = [header, "─" * len(header)]
    for i, r in enumerate(ranked, 1):
        score = f"{r.icp_score:.2f}" if r.icp_score is not None else "  -"
        lines.append(
            f"{i:>3} {cell(r.company_name, 22)} {cell(r.founder_name, 18)} "
            f"{cell(r.founder_role, 12)} {cell(r.domain, 22)} {score:>5} "
            f"{cell(r.score_reason, 42)} {cell(r.source_url, 30)}"
        )
    return "\n".join(lines)


def ranked(rows: list[DiscoveryCandidate]) -> list[DiscoveryCandidate]:
    """The same order the table shows — selection indexes resolve against this."""
    return sorted(
        rows, key=lambda r: r.icp_score if r.icp_score is not None else -1.0, reverse=True
    )
