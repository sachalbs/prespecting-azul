"""Prospeo `enrich-person`: find + verify the email AND return a rich dossier.

One call does sourcing (verified email) and seeds research (headline, job history,
company funding, active job postings). Free tier may *mask* the email
(e.g. "john.****@acme.com") — masked == not sendable, surfaced as RISKY.
Docs: https://prospeo.io/api-docs/enrich-person
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.enums import EmailStatus
from azul.errors import ConfigError, SourcingError
from azul.sourcing.base import EmailVerification, EmailVerifier

_STATUS_MAP = {
    "VERIFIED": EmailStatus.VERIFIED,
    "VALID": EmailStatus.VERIFIED,
    "INVALID": EmailStatus.INVALID,
    "UNDELIVERABLE": EmailStatus.INVALID,
    "CATCH_ALL": EmailStatus.RISKY,
    "ACCEPT_ALL": EmailStatus.RISKY,
    "UNKNOWN": EmailStatus.UNKNOWN,
}


def _split_name(full_name: str | None) -> tuple[str, str] | None:
    if not full_name:
        return None
    parts = full_name.split()
    if len(parts) == 1:
        return parts[0], parts[0]
    return parts[0], " ".join(parts[1:])


def summarize_dossier(raw: dict[str, Any]) -> dict[str, Any]:
    """Trim the enrich response to high-signal hook material (stored on the prospect)."""
    person = raw.get("person") or {}
    company = raw.get("company") or {}
    funding = company.get("funding") or {}
    jobs = company.get("job_postings") or {}
    history = person.get("job_history") or []
    return {
        "headline": person.get("headline"),
        "current_title": person.get("current_job_title"),
        "linkedin_url": person.get("linkedin_url"),
        "latest_role": history[0] if history else None,
        "company_description": company.get("description_ai") or company.get("description"),
        "company_keywords": (company.get("keywords") or [])[:8],
        "latest_funding": (funding.get("funding_events") or [None])[0],
        "active_job_titles": jobs.get("active_titles") or [],
    }


class ProspeoVerifier(EmailVerifier):
    name: ClassVar[str] = "prospeo"

    def __init__(self, timeout: float = 30.0) -> None:
        key = get_settings().prospeo_api_key
        if not key:
            raise ConfigError("PROSPEO_API_KEY required for SOURCING_PROVIDER=prospeo")
        self._client = httpx.Client(
            base_url="https://api.prospeo.io",
            headers={"X-KEY": key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        name = _split_name(full_name)
        if name is None or not company_domain:
            return EmailVerification(email=email, status=EmailStatus.UNKNOWN, provider=self.name)
        payload = {
            "only_verified_email": True,
            "enrich_mobile": False,
            "data": {
                "first_name": name[0],
                "last_name": name[1],
                "company_website": company_domain,
            },
        }
        try:
            resp = self._client.post("/enrich-person", json=payload)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
        except httpx.HTTPError as exc:
            raise SourcingError(f"Prospeo enrich failed: {exc}") from exc

        if data.get("error"):
            return EmailVerification(
                email=email, status=EmailStatus.INVALID, provider=self.name, raw=data
            )

        email_block = (data.get("person") or {}).get("email") or {}
        found = email_block.get("email") or email
        status = _STATUS_MAP.get(str(email_block.get("status", "")).upper(), EmailStatus.UNKNOWN)
        # A masked email cannot be sent to — treat as risky, not verified.
        if "*" in str(found):
            status = EmailStatus.RISKY
        return EmailVerification(
            email=found,
            status=status,
            provider=self.name,
            raw=data,
            dossier=summarize_dossier(data),
        )
