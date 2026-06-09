"""Deterministic stub discoverer — exercises the discover -> approve-list flow offline."""

from __future__ import annotations

from typing import ClassVar

from azul.discovery.base import Discoverer, Lead
from azul.logging import get_logger

log = get_logger(__name__)


class StubDiscoverer(Discoverer):
    name: ClassVar[str] = "stub"

    def discover(self, icp_brief: str, limit: int = 25) -> list[Lead]:
        log.info("stub_discover", brief=icp_brief[:120], limit=limit)
        n = min(limit, 5)
        return [
            Lead(
                full_name=f"Prospect {i}",
                company=f"Studio{i}",
                company_domain=f"studio{i}.example",
                title="Founder",
                source_url="stub://search",
            )
            for i in range(1, n + 1)
        ]
