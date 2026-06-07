"""Pick the channel backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.connectors.base import Channel
from azul.connectors.stub import StubChannel


def get_channel() -> Channel:
    if get_settings().channel == "graph":
        from azul.connectors.graph import GraphChannel

        return GraphChannel()
    return StubChannel()
