"""Discovery dedup: never the same domain twice — in batch or against the base.

"Against the base" covers both already-contacted (prospects: company_domain and
email domains) and already-discovered (discovery_candidates), so a re-run of
discovery never re-surfaces someone the tenant has already seen.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from azul.db.models import DiscoveryCandidate, Prospect
from azul.discovery.base import ProspectCandidate
from azul.logging import get_logger

log = get_logger(__name__)


def _norm(domain: str) -> str:
    d = domain.strip().lower()
    return d[4:] if d.startswith("www.") else d


def known_domains(session: Session, tenant_id: uuid.UUID) -> set[str]:
    """Domains the tenant already has: contacted prospects + past discoveries."""
    known: set[str] = set()
    rows = session.execute(
        select(Prospect.company_domain, Prospect.email).where(Prospect.tenant_id == tenant_id)
    ).all()
    for company_domain, email in rows:
        if company_domain:
            known.add(_norm(str(company_domain)))
        if email and "@" in str(email):
            known.add(_norm(str(email).rsplit("@", 1)[1]))
    for (domain,) in session.execute(
        select(DiscoveryCandidate.domain).where(DiscoveryCandidate.tenant_id == tenant_id)
    ).all():
        known.add(_norm(str(domain)))
    return known


def dedupe(
    session: Session, tenant_id: uuid.UUID, candidates: list[ProspectCandidate]
) -> list[ProspectCandidate]:
    """Drop in-batch domain duplicates and anything the tenant already knows."""
    known = known_domains(session, tenant_id)
    seen: set[str] = set()
    out: list[ProspectCandidate] = []
    for candidate in candidates:
        domain = _norm(candidate.domain)
        if not domain or domain in known or domain in seen:
            continue
        seen.add(domain)
        candidate.domain = domain
        out.append(candidate)
    if len(out) != len(candidates):
        log.info("discovery_deduped", before=len(candidates), after=len(out))
    return out
