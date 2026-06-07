"""Waterfall verifier: Prospeo -> Hunter -> Dropcontact.

Stops at the first confident verdict (verified/invalid); otherwise falls through.
Keeps the best non-confident result so we never claim more than we know.
"""

from __future__ import annotations

from typing import ClassVar

from azul.config import get_settings
from azul.enums import EmailStatus
from azul.errors import ConfigError, SourcingError
from azul.logging import get_logger
from azul.sourcing.base import EmailVerification, EmailVerifier

log = get_logger(__name__)

_CONFIDENT = {EmailStatus.VERIFIED, EmailStatus.INVALID}


class WaterfallVerifier(EmailVerifier):
    name: ClassVar[str] = "waterfall"

    def __init__(self) -> None:
        s = get_settings()
        providers: list[EmailVerifier] = []
        if s.prospeo_api_key:
            from azul.sourcing.providers.prospeo import ProspeoVerifier

            providers.append(ProspeoVerifier())
        if s.hunter_api_key:
            from azul.sourcing.providers.hunter import HunterVerifier

            providers.append(HunterVerifier())
        if s.dropcontact_api_key:
            from azul.sourcing.providers.dropcontact import DropcontactVerifier

            providers.append(DropcontactVerifier())
        if not providers:
            raise ConfigError(
                "SOURCING_PROVIDER=waterfall needs at least one of "
                "PROSPEO_API_KEY / HUNTER_API_KEY / DROPCONTACT_API_KEY"
            )
        self._providers = providers

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        best: EmailVerification | None = None
        for provider in self._providers:
            try:
                result = provider.verify(email, full_name=full_name, company_domain=company_domain)
            except SourcingError as exc:
                log.warning("verifier_error", provider=provider.name, error=str(exc))
                continue
            if result.status in _CONFIDENT:
                return result
            best = best or result
        return best or EmailVerification(
            email=email, status=EmailStatus.UNKNOWN, provider=self.name
        )
