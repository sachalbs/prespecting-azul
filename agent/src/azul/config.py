"""Typed settings, sourced from environment / `.env`. Secrets never live in code."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SourcingProvider = Literal["stub", "prospeo", "waterfall"]
ResearchEngineName = Literal["stub", "holo3"]
WriterProvider = Literal["stub", "openai_compat"]
ChannelName = Literal["stub", "graph"]


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

    # Sourcing (Prospeo enrich = find + verify + dossier; Hunter/Dropcontact optional)
    prospeo_api_key: str | None = None
    hunter_api_key: str | None = None
    dropcontact_api_key: str | None = None

    # Research — Holo3 computer-use (OpenAI-compatible, drives a headless browser)
    hai_api_key: str | None = None
    holo_base_url: str = "https://api.hcompany.ai/v1"
    holo_model: str = "holo3-1-35b-a3b"
    holo_max_steps: int = 25
    holo_timeout_s: int = 120
    holo_headless: bool = True
    # Path to a Playwright storage_state JSON with a logged-in LinkedIn session.
    linkedin_storage_state: str | None = None

    # Writer (GLM-5.1 / DeepSeek V4 — OpenAI-compatible). Playbook = system prompt.
    writer_api_key: str | None = None
    writer_base_url: str | None = None
    writer_model: str | None = None
    writer_temperature: float = 0.7
    writer_playbook_path: str = "AZUL_COLD_OUTREACH_PLAYBOOK.md"

    # Connector — Microsoft Graph (Outlook), send from the real mailbox + poll replies
    graph_client_id: str | None = None
    # Personal Outlook accounts live under the "consumers" tenant.
    graph_authority: str = "https://login.microsoftonline.com/consumers"
    graph_token_cache: str = ".msal_cache.bin"
    webhook_secret: str | None = None

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
