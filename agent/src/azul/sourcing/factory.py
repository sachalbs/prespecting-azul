"""Pick the verifier backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.sourcing.base import EmailVerifier
from azul.sourcing.stub import StubVerifier


def get_verifier() -> EmailVerifier:
    provider = get_settings().sourcing_provider
    if provider == "finder":
        # In-house critical path: permutations + MX/SMTP, no paid API required.
        from azul.sourcing.finder import FinderVerifier
        from azul.sourcing.verifier import SmtpVerifier

        return FinderVerifier(SmtpVerifier())
    if provider == "prospeo":
        from azul.sourcing.providers.prospeo import ProspeoVerifier

        return ProspeoVerifier()
    if provider == "waterfall":
        from azul.sourcing.waterfall import WaterfallVerifier

        return WaterfallVerifier()
    return StubVerifier()
