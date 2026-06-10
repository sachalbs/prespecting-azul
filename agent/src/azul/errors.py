"""Typed error hierarchy."""

from __future__ import annotations


class AzulError(Exception):
    """Base for all Azul errors."""


class ConfigError(AzulError):
    """Missing/invalid configuration (e.g. an adapter selected without its key)."""


class SourcingError(AzulError):
    pass


class ResearchError(AzulError):
    pass


class WritingError(AzulError):
    pass


class ChannelError(AzulError):
    pass


class LLMError(AzulError):
    """A generic LLM call (brief, discovery, scoring) failed or returned junk."""
