"""`EmailVerifier` contract. Deliverability gate: bounce-risk addresses never send."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from azul.enums import EmailStatus

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def looks_like_email(value: str) -> bool:
    return bool(_EMAIL_RE.match(value.strip()))


@dataclass
class EmailVerification:
    email: str
    status: EmailStatus
    provider: str
    score: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def sendable(self) -> bool:
        return self.status == EmailStatus.VERIFIED


class EmailVerifier(ABC):
    name: ClassVar[str]

    @abstractmethod
    def verify(
        self, email: str, *, full_name: str | None = None, company_domain: str | None = None
    ) -> EmailVerification:
        raise NotImplementedError
