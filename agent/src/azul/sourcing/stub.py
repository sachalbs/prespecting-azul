"""Stub verifier — no external calls. Syntactically valid == verified."""

from __future__ import annotations

from typing import ClassVar

from azul.enums import EmailStatus
from azul.sourcing.base import EmailVerification, EmailVerifier, looks_like_email


class StubVerifier(EmailVerifier):
    name: ClassVar[str] = "stub"

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        status = EmailStatus.VERIFIED if looks_like_email(email) else EmailStatus.INVALID
        return EmailVerification(email=email, status=status, provider=self.name, score=1.0)
