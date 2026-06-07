"""Dropcontact verifier (skeleton).

Dropcontact is async/batch (submit -> poll). TODO(dropcontact-docs): implement the
poll loop and response mapping before live. Used last in the waterfall.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx

from azul.config import get_settings
from azul.enums import EmailStatus
from azul.errors import ConfigError, SourcingError
from azul.sourcing.base import EmailVerification, EmailVerifier


class DropcontactVerifier(EmailVerifier):
    name: ClassVar[str] = "dropcontact"

    def __init__(self, timeout: float = 30.0) -> None:
        key = get_settings().dropcontact_api_key
        if not key:
            raise ConfigError("DROPCONTACT_API_KEY required for the Dropcontact verifier")
        self._client = httpx.Client(
            base_url="https://api.dropcontact.com",
            headers={"X-Access-Token": key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        try:
            # TODO(dropcontact-docs): submit batch + poll /batch/{id} for the result.
            resp = self._client.post("/batch", json={"data": [{"email": email}]})
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            raise SourcingError(f"Dropcontact verify failed: {exc}") from exc

        # Pending the poll loop, treat as unknown so the waterfall stays honest.
        return EmailVerification(
            email=email, status=EmailStatus.UNKNOWN, provider=self.name, raw=data
        )
