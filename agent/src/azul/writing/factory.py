"""Pick the writer backend from settings."""

from __future__ import annotations

from azul.config import get_settings
from azul.writing.base import Writer
from azul.writing.stub import StubWriter


def get_writer() -> Writer:
    provider = get_settings().writer_provider
    if provider == "openai_compat":
        from azul.writing.openai_compat import OpenAICompatWriter

        return OpenAICompatWriter()
    return StubWriter()
