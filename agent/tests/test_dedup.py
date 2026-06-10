"""Dedup: never the same domain twice — in batch, in prospects, in past discoveries."""

from __future__ import annotations

from azul.db.models import DiscoveryCandidate, Prospect
from azul.db.session import session_scope
from azul.discovery.base import ProspectCandidate
from azul.discovery.dedup import dedupe
from azul.orchestrator.campaign import ensure_tenant


def _c(domain: str) -> ProspectCandidate:
    return ProspectCandidate(company_name=domain.split(".")[0].title(), domain=domain)


def test_in_batch_duplicates_collapse() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t1")
        out = dedupe(s, tenant.id, [_c("alpha.fr"), _c("www.alpha.fr"), _c("beta.fr")])
    assert [c.domain for c in out] == ["alpha.fr", "beta.fr"]


def test_already_contacted_domains_excluded() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t1")
        s.add(
            Prospect(
                tenant_id=tenant.id, email="ann@alpha.fr",
                company_domain="alpha.fr", source="csv",
            )
        )
        s.add(Prospect(tenant_id=tenant.id, email="bob@gamma.io", source="csv"))
        s.flush()
        out = dedupe(
            s, tenant.id, [_c("alpha.fr"), _c("gamma.io"), _c("delta.fr")]
        )
    # alpha.fr via company_domain, gamma.io via the prospect's email domain
    assert [c.domain for c in out] == ["delta.fr"]


def test_already_discovered_domains_excluded() -> None:
    with session_scope() as s:
        tenant = ensure_tenant(s, "t1")
        s.add(
            DiscoveryCandidate(
                tenant_id=tenant.id, company_name="Vu Déjà", domain="deja.fr"
            )
        )
        s.flush()
        out = dedupe(s, tenant.id, [_c("deja.fr"), _c("neuf.fr")])
    assert [c.domain for c in out] == ["neuf.fr"]


def test_other_tenants_domains_do_not_leak_into_dedup() -> None:
    with session_scope() as s:
        t1 = ensure_tenant(s, "t1")
        t2 = ensure_tenant(s, "t2")
        s.add(Prospect(tenant_id=t2.id, email="x@autre.fr", company_domain="autre.fr"))
        s.flush()
        out = dedupe(s, t1.id, [_c("autre.fr")])
    assert [c.domain for c in out] == ["autre.fr"]  # t2's history is not t1's
