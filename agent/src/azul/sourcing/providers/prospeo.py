"""Prospeo email-verifier adapter (skeleton).

TODO(prospeo-docs): confirm endpoint, auth header, and response schema before live.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx

from azul.config import get_settings
from azul.enums import EmailStatus
from azul.errors import ConfigError, SourcingError
from azul.sourcing.base import EmailVerification, EmailVerifier

_STATUS_MAP = {
    "valid": EmailStatus.VERIFIED,
    "deliverable": EmailStatus.VERIFIED,
    "invalid": EmailStatus.INVALID,
    "undeliverable": EmailStatus.INVALID,
    "risky": EmailStatus.RISKY,
    "catch_all": EmailStatus.RISKY,
    "unknown": EmailStatus.UNKNOWN,
}


class ProspeoVerifier(EmailVerifier):
    name: ClassVar[str] = "prospeo"

    def __init__(self, timeout: float = 30.0) -> None:
        key = get_settings().prospeo_api_key
        if not key:
            raise ConfigError("PROSPEO_API_KEY required for the Prospeo verifier")
        self._client = httpx.Client(
            base_url="https://api.prospeo.io",
            headers={"X-KEY": key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        try:
            resp = self._client.post("/email-verifier", json={"email": email})
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            raise SourcingError(f"Prospeo verify failed: {exc}") from exc

        # TODO(prospeo-docs): map the real response field to a status string.
        raw_status = str((data.get("response") or data).get("status", "unknown")).lower()
        return EmailVerification(
            email=email,
            status=_STATUS_MAP.get(raw_status, EmailStatus.UNKNOWN),
            provider=self.name,
            raw=data,
        )
