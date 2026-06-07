"""Typed settings, sourced from environment / `.env`. Secrets never live in code."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SourcingProvider = Literal["stub", "waterfall"]
ResearchEngineName = Literal["stub", "holo3"]
WriterProvider = Literal["stub", "openai_compat"]
ChannelName = Literal["stub", "unipile"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Runtime
    environment: str = "dev"
    log_level: str = "INFO"
    log_json: bool = False

    # Database — Postgres+pgvector in prod, sqlite fallback for zero-infra runs
    database_url: str = "sqlite:///azul.db"

    # Which adapter backs each interface (stub today, live once keys land)
    sourcing_provider: SourcingProvider = "stub"
    research_engine: ResearchEngineName = "stub"
    writer_provider: WriterProvider = "stub"
    channel: ChannelName = "stub"

    # Sourcing waterfall
    prospeo_api_key: str | None = None
    hunter_api_key: str | None = None
    dropcontact_api_key: str | None = None

    # Research (Holo3)
    holo3_api_key: str | None = None
    holo3_base_url: str = "https://api.holo3.ai"

    # Writer (GLM-5.1 / DeepSeek V4 — OpenAI-compatible)
    writer_api_key: str | None = None
    writer_base_url: str | None = None
    writer_model: str | None = None
    writer_temperature: float = 0.7

    # Connector (Unipile)
    unipile_api_key: str | None = None
    unipile_dsn: str | None = None
    unipile_account_id: str | None = None
    unipile_webhook_secret: str | None = None

    # Deliverability — pace sends, never spray
    send_min_delay_seconds: int = 45
    send_max_delay_seconds: int = 180
    daily_send_cap: int = 25

    # Flywheel (later) — skills embedding dimension
    embedding_dim: int = Field(default=1024, ge=1)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
