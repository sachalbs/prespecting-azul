"""In-house email verifier: syntax + MX always; SMTP RCPT handshake when enabled.

Step 1 (always): syntax check + MX lookup via dnspython — no mail infra means the
address can't receive, full stop.
Step 2 (VERIFY_SMTP=true, needs outbound port 25 — the VPS case): connect to the
top-priority MX, `RCPT TO` the address, and probe a random local part to detect
catch-all domains (which accept everything, so acceptance proves nothing).

Verdicts (logic inspired by AfterShip/email-verifier, MIT):
  VALID      RCPT accepted and the domain is not catch-all      (confidence 0.90)
  INVALID    bad syntax / no MX+A / RCPT rejected with 5xx      (confidence 0.95+)
  CATCH_ALL  RCPT accepted but so is a random address           (confidence 0.50)
  UNKNOWN    SMTP disabled, greylisting (4xx), or network error (confidence ≤0.40)

Send policy downstream: INVALID = skip; CATCH_ALL/UNKNOWN = allowed, flagged.
"""

from __future__ import annotations

import smtplib
import uuid
from typing import ClassVar

import dns.exception
import dns.resolver

from azul.config import get_settings
from azul.enums import EmailStatus, VerifyStatus
from azul.logging import get_logger
from azul.sourcing.base import EmailVerification, EmailVerifier, looks_like_email

log = get_logger(__name__)

_HELO = "verifier.local"
_PROBE_FROM = f"probe@{_HELO}"

_TO_EMAIL_STATUS = {
    VerifyStatus.VALID: EmailStatus.VERIFIED,
    VerifyStatus.INVALID: EmailStatus.INVALID,
    VerifyStatus.CATCH_ALL: EmailStatus.RISKY,
    VerifyStatus.UNKNOWN: EmailStatus.UNKNOWN,
}


def resolve_mx(domain: str) -> list[str] | None:
    """MX hosts by priority; falls back to the A record; None = no mail infra.

    An empty list means the lookup itself failed (DNS timeout) — indeterminate.
    """
    try:
        answers = dns.resolver.resolve(domain, "MX")
        hosts = sorted(
            (r.preference, str(r.exchange).rstrip(".")) for r in answers  # type: ignore[attr-defined]
        )
        return [h for _, h in hosts if h]
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return None
    except dns.resolver.NoAnswer:
        pass
    except dns.exception.DNSException:
        return []
    try:  # no MX record — RFC 5321 falls back to the A record
        dns.resolver.resolve(domain, "A")
        return [domain]
    except dns.exception.DNSException:
        return None


def smtp_rcpt_code(host: str, email: str, timeout: float) -> int | None:
    """RCPT TO reply code from the MX, or None on any network/protocol failure."""
    try:
        with smtplib.SMTP(host, 25, timeout=timeout) as smtp:
            smtp.helo(_HELO)
            smtp.mail(_PROBE_FROM)
            code, _ = smtp.rcpt(email)
            return code
    except (smtplib.SMTPException, OSError):
        return None


class SmtpVerifier(EmailVerifier):
    name: ClassVar[str] = "smtp"

    def __init__(self, smtp_enabled: bool | None = None, timeout: float = 10.0) -> None:
        self._smtp_enabled = get_settings().verify_smtp if smtp_enabled is None else smtp_enabled
        self._timeout = timeout
        self._catch_all_cache: dict[str, bool] = {}

    def _is_catch_all(self, mx_host: str, domain: str) -> bool | None:
        if domain in self._catch_all_cache:
            return self._catch_all_cache[domain]
        probe = f"azul-{uuid.uuid4().hex[:12]}@{domain}"
        code = smtp_rcpt_code(mx_host, probe, self._timeout)
        if code is None:
            return None
        result = 200 <= code < 300
        self._catch_all_cache[domain] = result
        return result

    def _result(
        self, email: str, verdict: VerifyStatus, confidence: float, **raw: object
    ) -> EmailVerification:
        return EmailVerification(
            email=email,
            status=_TO_EMAIL_STATUS[verdict],
            provider=self.name,
            score=confidence,
            verdict=verdict,
            raw={"catch_all": verdict == VerifyStatus.CATCH_ALL, **raw},
        )

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        email = email.strip().lower()
        if not looks_like_email(email):
            return self._result(email, VerifyStatus.INVALID, 1.0, reason="syntax")

        domain = email.split("@", 1)[1]
        mx_hosts = resolve_mx(domain)
        if mx_hosts is None:
            return self._result(email, VerifyStatus.INVALID, 0.95, reason="no_mx")
        if not mx_hosts:  # DNS lookup itself failed — can't tell
            return self._result(email, VerifyStatus.UNKNOWN, 0.2, reason="dns_error")
        if not self._smtp_enabled:
            return self._result(
                email, VerifyStatus.UNKNOWN, 0.4, reason="smtp_disabled", mx=mx_hosts[0]
            )

        code = smtp_rcpt_code(mx_hosts[0], email, self._timeout)
        if code is None:
            return self._result(email, VerifyStatus.UNKNOWN, 0.3, reason="smtp_error")
        if 500 <= code < 600:
            return self._result(email, VerifyStatus.INVALID, 0.95, reason=f"rcpt_{code}")
        if not 200 <= code < 300:  # 4xx greylisting and friends
            return self._result(email, VerifyStatus.UNKNOWN, 0.3, reason=f"rcpt_{code}")

        catch_all = self._is_catch_all(mx_hosts[0], domain)
        if catch_all:
            return self._result(email, VerifyStatus.CATCH_ALL, 0.5)
        confidence = 0.9 if catch_all is False else 0.7  # None = probe failed
        return self._result(email, VerifyStatus.VALID, confidence)
