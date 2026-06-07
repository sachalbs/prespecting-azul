"""Hunter email-verifier adapter. (Endpoint is stable; mapping verified below.)"""

from __future__ import annotations

from typing import ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.enums import EmailStatus
from azul.errors import ConfigError, SourcingError
from azul.sourcing.base import EmailVerification, EmailVerifier

_STATUS_MAP = {
    "valid": EmailStatus.VERIFIED,
    "invalid": EmailStatus.INVALID,
    "disposable": EmailStatus.INVALID,
    "accept_all": EmailStatus.RISKY,
    "webmail": EmailStatus.RISKY,
    "unknown": EmailStatus.UNKNOWN,
}


class HunterVerifier(EmailVerifier):
    name: ClassVar[str] = "hunter"

    def __init__(self, timeout: float = 30.0) -> None:
        key = get_settings().hunter_api_key
        if not key:
            raise ConfigError("HUNTER_API_KEY required for the Hunter verifier")
        self._key = key
        self._client = httpx.Client(base_url="https://api.hunter.io", timeout=timeout)

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        try:
            resp = self._client.get(
                "/v2/email-verifier", params={"email": email, "api_key": self._key}
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
        except httpx.HTTPError as exc:
            raise SourcingError(f"Hunter verify failed: {exc}") from exc

        status = _STATUS_MAP.get(data.get("status", "unknown"), EmailStatus.UNKNOWN)
        score = data.get("score")
        return EmailVerification(
            email=email,
            status=status,
            provider=self.name,
            score=float(score) / 100.0 if isinstance(score, (int, float)) else None,
            raw=data,
        )
