"""Pick the channel backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.connectors.base import Channel
from azul.connectors.stub import StubChannel


def get_channel() -> Channel:
    if get_settings().channel == "unipile":
        from azul.connectors.unipile import UnipileChannel

        return UnipileChannel()
    return StubChannel()
