"""Email finder: name@domain permutations, each checked by a verifier — first hit wins.

Replaces paid enrichment on the critical path: a hand-picked prospect has
full_name + company_domain; the finder derives candidate addresses and delegates
each to the wrapped verifier (MX/SMTP or any other `EmailVerifier`). If the
domain's pattern is already known — fed in upfront (public email found during
research) or learned from an earlier verified hit in the run — it is tried first.
"""

from __future__ import annotations

import re
import unicodedata
from typing import ClassVar

from azul.enums import EmailStatus
from azul.logging import get_logger
from azul.sourcing.base import EmailVerification, EmailVerifier, looks_like_email

log = get_logger(__name__)

# Most-common corporate patterns first; {f} is the first-name initial.
PATTERNS = ("{first}.{last}", "{f}{last}", "{first}", "{last}", "{first}-{last}")

_KEEP = re.compile(r"[^a-z0-9]")


def _normalize(part: str) -> str:
    """Lowercase ASCII, accents stripped: 'Éloïse' -> 'eloise'."""
    ascii_part = unicodedata.normalize("NFKD", part).encode("ascii", "ignore").decode()
    return _KEEP.sub("", ascii_part.lower())


def _split_name(full_name: str) -> tuple[str, str] | None:
    parts = [p for p in (_normalize(p) for p in full_name.split()) if p]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], parts[-1]


def pattern_of(email: str, full_name: str) -> str | None:
    """Which known pattern produced this address? (Used to learn a domain's habit.)"""
    name = _split_name(full_name)
    if name is None or "@" not in email:
        return None
    first, last = name
    local = email.split("@", 1)[0].lower()
    for pattern in PATTERNS:
        if pattern.format(first=first, last=last, f=first[:1]) == local:
            return pattern
    return None


def candidates(full_name: str, domain: str, known_pattern: str | None = None) -> list[str]:
    """Ordered candidate addresses for a person on a domain (known pattern first)."""
    name = _split_name(full_name)
    if name is None or not domain:
        return []
    first, last = name
    ordered = list(PATTERNS)
    if known_pattern in ordered:
        ordered.remove(known_pattern)
        ordered.insert(0, known_pattern)
    seen: set[str] = set()
    out: list[str] = []
    for pattern in ordered:
        local = pattern.format(first=first, last=last, f=first[:1])
        email = f"{local}@{domain.lower()}"
        if local and email not in seen:
            seen.add(email)
            out.append(email)
    return out


class FinderVerifier(EmailVerifier):
    """Find + verify behind the standard `EmailVerifier` interface."""

    name: ClassVar[str] = "finder"

    def __init__(
        self, verifier: EmailVerifier, domain_patterns: dict[str, str] | None = None
    ) -> None:
        self._verifier = verifier
        # domain -> pattern; seeded by the caller, then learned from verified hits.
        self._domain_patterns: dict[str, str] = dict(domain_patterns or {})

    def _learn(self, email: str, full_name: str | None) -> None:
        if not full_name or "@" not in email:
            return
        pattern = pattern_of(email, full_name)
        if pattern:
            self._domain_patterns[email.split("@", 1)[1].lower()] = pattern

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        best: EmailVerification | None = None

        # An explicit address always gets first shot.
        if email and looks_like_email(email):
            result = self._verifier.verify(
                email, full_name=full_name, company_domain=company_domain
            )
            if result.status == EmailStatus.VERIFIED:
                self._learn(result.email, full_name)
                return result
            best = result

        if full_name and company_domain:
            known = self._domain_patterns.get(company_domain.lower())
            for candidate in candidates(full_name, company_domain, known):
                if candidate == email:
                    continue  # already tried above
                result = self._verifier.verify(
                    candidate, full_name=full_name, company_domain=company_domain
                )
                if result.status == EmailStatus.VERIFIED:
                    self._learn(result.email, full_name)
                    log.info("email_found", email=result.email)
                    return result
                if best is None or _rank(result.status) > _rank(best.status):
                    best = result
                # A catch-all domain accepts every local part — further probes
                # are indistinguishable, stop burning SMTP calls.
                if result.raw.get("catch_all"):
                    break

        return best or EmailVerification(
            email=email, status=EmailStatus.UNKNOWN, provider=self.name
        )


def _rank(status: EmailStatus) -> int:
    """Preference order for a non-verified fallback result."""
    return {
        EmailStatus.RISKY: 2,
        EmailStatus.UNKNOWN: 1,
        EmailStatus.INVALID: 0,
    }.get(status, 0)
