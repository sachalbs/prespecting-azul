"""Email find + verify, behind a swappable provider. Verify before any send."""

from azul.sourcing.base import EmailVerification, EmailVerifier
from azul.sourcing.factory import get_verifier

__all__ = ["EmailVerification", "EmailVerifier", "get_verifier"]
