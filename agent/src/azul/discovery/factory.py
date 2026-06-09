"""Pick the discovery backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.discovery.base import Discoverer
from azul.discovery.stub import StubDiscoverer


def get_discoverer() -> Discoverer:
    if get_settings().discovery_provider == "websearch":
        from azul.discovery.websearch import WebSearchDiscoverer

        return WebSearchDiscoverer()
    return StubDiscoverer()
