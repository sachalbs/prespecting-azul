"""Finder: permutations in priority order, first VALID wins, domain pattern learned."""

from __future__ import annotations

from typing import ClassVar

import pytest

from azul.enums import EmailStatus
from azul.sourcing.base import EmailVerification, EmailVerifier
from azul.sourcing.finder import FinderVerifier, candidates, pattern_of


class MapVerifier(EmailVerifier):
    """Deterministic verifier: a known set of valid addresses, everything else invalid."""

    name: ClassVar[str] = "map"

    def __init__(
        self, valid: set[str], catch_all_domains: set[str] | None = None
    ) -> None:
        self.valid = valid
        self.catch_all_domains = catch_all_domains or set()
        self.calls: list[str] = []

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        self.calls.append(email)
        domain = email.split("@", 1)[1] if "@" in email else ""
        if domain in self.catch_all_domains:
            return EmailVerification(
                email=email, status=EmailStatus.RISKY, provider=self.name,
                raw={"catch_all": True},
            )
        status = EmailStatus.VERIFIED if email in self.valid else EmailStatus.INVALID
        return EmailVerification(email=email, status=status, provider=self.name)


def test_candidates_order_and_accents() -> None:
    got = candidates("Éloïse Van Müller", "Acme.com")
    assert got[0] == "eloise.muller@acme.com"  # accents stripped, last token = last name
    assert "emuller@acme.com" in got
    assert "eloise-muller@acme.com" in got
    assert all(e.endswith("@acme.com") for e in got)


def test_known_pattern_tried_first() -> None:
    got = candidates("Ann Lee", "acme.com", known_pattern="{f}{last}")
    assert got[0] == "alee@acme.com"


def test_first_valid_wins() -> None:
    inner = MapVerifier(valid={"alee@acme.com"})
    result = FinderVerifier(inner).verify("", full_name="Ann Lee", company_domain="acme.com")
    assert result.status == EmailStatus.VERIFIED
    assert result.email == "alee@acme.com"
    # Stopped as soon as it hit the valid one.
    assert inner.calls[-1] == "alee@acme.com"


def test_explicit_email_gets_first_shot() -> None:
    inner = MapVerifier(valid={"ann@acme.com"})
    result = FinderVerifier(inner).verify(
        "ann@acme.com", full_name="Ann Lee", company_domain="acme.com"
    )
    assert result.status == EmailStatus.VERIFIED
    assert inner.calls == ["ann@acme.com"]


def test_verified_hit_teaches_the_domain_pattern() -> None:
    inner = MapVerifier(valid={"alee@acme.com", "bstone@acme.com"})
    finder = FinderVerifier(inner)
    finder.verify("", full_name="Ann Lee", company_domain="acme.com")
    inner.calls.clear()
    result = finder.verify("", full_name="Bob Stone", company_domain="acme.com")
    assert result.email == "bstone@acme.com"
    assert inner.calls[0] == "bstone@acme.com"  # learned {f}{last}, tried first


def test_catch_all_short_circuits_and_flags_risky() -> None:
    inner = MapVerifier(valid=set(), catch_all_domains={"ghost.io"})
    result = FinderVerifier(inner).verify("", full_name="Bob Stone", company_domain="ghost.io")
    assert result.status == EmailStatus.RISKY
    assert len(inner.calls) == 1  # no point probing a catch-all five times


def test_nothing_found_returns_unknown_or_invalid_not_verified() -> None:
    inner = MapVerifier(valid=set())
    result = FinderVerifier(inner).verify("", full_name="Ann Lee", company_domain="acme.com")
    assert result.status != EmailStatus.VERIFIED


def test_pattern_of_recognises_locals() -> None:
    assert pattern_of("ann.lee@acme.com", "Ann Lee") == "{first}.{last}"
    assert pattern_of("alee@acme.com", "Ann Lee") == "{f}{last}"
    assert pattern_of("contact@acme.com", "Ann Lee") is None


def test_factory_returns_finder_without_any_paid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """SOURCING_PROVIDER=finder needs no Prospeo/Hunter/Dropcontact key."""
    from azul.config import get_settings
    from azul.sourcing.factory import get_verifier

    monkeypatch.setenv("SOURCING_PROVIDER", "finder")
    get_settings.cache_clear()
    try:
        verifier = get_verifier()
        assert isinstance(verifier, FinderVerifier)
    finally:
        get_settings.cache_clear()
