"""Typed settings, sourced from environment / `.env`. Secrets never live in code."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DiscoveryProvider = Literal["stub", "websearch"]
SourcingProvider = Literal["stub", "finder", "prospeo", "waterfall"]
ResearchEngineName = Literal["stub", "dossier", "tavily", "tiered", "holo3"]
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
    discovery_provider: DiscoveryProvider = "stub"
    sourcing_provider: SourcingProvider = "stub"
    research_engine: ResearchEngineName = "stub"
    writer_provider: WriterProvider = "stub"
    channel: ChannelName = "stub"

    # Discovery (web search → leads). Provider TBD (Brave/Serper/Bing) via these.
    search_api_key: str | None = None
    search_api_url: str | None = None
    # Brief-driven web discovery: cap on Tavily calls (search + extract) per run.
    discovery_max_searches: int = 15

    # Sourcing (Prospeo enrich = find + verify + dossier; Hunter/Dropcontact optional)
    prospeo_api_key: str | None = None
    hunter_api_key: str | None = None
    dropcontact_api_key: str | None = None

    # In-house verifier: SMTP RCPT handshake (needs outbound port 25 — VPS only).
    # Off by default: syntax + MX checks still run, verdicts cap at UNKNOWN.
    verify_smtp: bool = False
    # Resolve a company's founder before the finder runs: cap Tavily calls/prospect.
    person_resolve_max_searches: int = 3

    # Research — Tavily (tier 1: search + extract, no browser)
    tavily_api_key: str | None = None
    # Tiered router: escalate to Holo when tier 1 yields <2 hooks at this confidence.
    research_tier_threshold: float = 0.6
    # Below this hook-strength score, don't force a hook — use a sober angle.
    hook_min_score: float = 0.5
    # Directory/aggregator domains: usable to FIND a prospect, never citable as a
    # hook source in the email (citing an annuaire = lazy research).
    directory_domains: str = (
        "trustfolio.co,trustfolio.com,sortlist.com,sortlist.fr,saleshandy.com,"
        "clutch.co,goodfirms.co,malt.fr,malt.com,societe.com,pappers.fr,"
        "trustpilot.com,glassdoor.com,glassdoor.fr,indeed.com,welcometothejungle.com"
    )

    # Research — Holo3 computer-use (OpenAI-compatible, drives a headless browser)
    hai_api_key: str | None = None
    holo_base_url: str = "https://api.hcompany.ai/v1"
    holo_model: str = "holo3-1-35b-a3b"
    holo_max_steps: int = 25
    holo_timeout_s: int = 120
    holo_headless: bool = True
    # Path to a Playwright storage_state JSON with a logged-in LinkedIn session.
    linkedin_storage_state: str | None = None

    # Writer (DeepSeek V4 default — OpenAI-compatible, env-driven). Playbook = system prompt.
    writer_api_key: str | None = None
    writer_base_url: str | None = None
    writer_model: str = "deepseek-chat"
    writer_temperature: float = 0.7
    writer_playbook_path: str = "AZUL_COLD_OUTREACH_PLAYBOOK.md"
    # Deterministic anti-slop style rules for the post-generation linter.
    style_rules_path: str = "style_rules.yaml"

    # Connector — Microsoft Graph (Outlook), send from the real mailbox + poll replies
    graph_client_id: str | None = None
    # Personal Outlook accounts live under the "consumers" tenant.
    graph_authority: str = "https://login.microsoftonline.com/consumers"
    graph_token_cache: str = ".msal_cache.bin"
    webhook_secret: str | None = None

    # Operator chat channel — manage Azul like an employee (Telegram now, WhatsApp next)
    telegram_bot_token: str | None = None

    # Public base URL of the agent worker (to build OAuth links sent into chat)
    public_base_url: str = "http://localhost:8000"

    # Deliverability — pace sends, never spray
    send_min_delay_seconds: int = 45
    send_max_delay_seconds: int = 180
    daily_send_cap: int = 25
    # Up to 3 seed mailboxes (comma-separated) for `azul deliverability-check`.
    seed_inboxes: str | None = None

    # Flywheel (later) — skills embedding dimension
    embedding_dim: int = Field(default=1024, ge=1)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def directory_domain_set(self) -> set[str]:
        return {d.strip().lower() for d in self.directory_domains.split(",") if d.strip()}

    @property
    def graph_redirect_uri(self) -> str:
        return f"{self.public_base_url.rstrip('/')}/oauth/outlook/callback"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
