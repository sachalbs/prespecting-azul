"""`azul` CLI: run-campaign -> review -> approve -> send-approved -> report.

The chat is the product; this CLI is the Jalon 0 stand-in until the Unipile chat
hook lands. Every command runs in a transactional session scope.
"""

from __future__ import annotations

import uuid

import typer

from azul.config import get_settings
from azul.db.session import get_engine, session_scope
from azul.logging import configure_logging
from azul.orchestrator import campaign as camp

app = typer.Typer(add_completion=False, help="Azul — autonomous deep-research SDR")


@app.callback()
def bootstrap() -> None:
    s = get_settings()
    configure_logging(level=s.log_level, json=s.log_json)


@app.command("init-db")
def init_db() -> None:
    """Create tables directly (dev convenience). Production uses Alembic migrations."""
    from azul.db import Base  # importing azul.db registers the ORM mappers

    Base.metadata.create_all(get_engine())
    typer.echo(f"Schema created on {get_settings().database_url}")


@app.command("run-campaign")
def run_campaign(
    tenant: str = typer.Option(..., help="Tenant slug"),
    name: str = typer.Option(..., help="Campaign name"),
    list_: str = typer.Option(..., "--list", help="Path to prospects CSV"),
    tenant_name: str | None = typer.Option(None, help="Tenant display name (first run)"),
    sender: str | None = typer.Option(None, help="Sender name for the message"),
    value_prop: str | None = typer.Option(None, help="One-line value prop"),
) -> None:
    """Source + research + write drafts for a CSV of prospects (stops at approval)."""
    rows = camp.load_prospects_csv(list_)
    typer.echo(f"Loaded {len(rows)} prospects from {list_}")
    with session_scope() as session:
        campaign = camp.run_campaign(
            session,
            tenant_slug=tenant,
            name=name,
            rows=rows,
            tenant_name=tenant_name,
            sender_name=sender,
            value_prop=value_prop,
        )
        drafts = camp.list_drafts(session, campaign.id)
        cid = campaign.id
        n = len(drafts)
    typer.echo(f"Campaign {cid} — {n} drafts ready for review.")
    typer.echo(f"Next: azul review --campaign {cid}")


@app.command("review")
def review(campaign: str = typer.Option(..., help="Campaign id or name")) -> None:
    """Print drafts awaiting approval."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        drafts = camp.list_drafts(session, c.id)
        if not drafts:
            typer.echo("No drafts awaiting approval.")
            return
        for m in drafts:
            typer.echo("─" * 72)
            typer.echo(f"id:      {m.id}")
            typer.echo(f"to:      {m.prospect.email}  ({m.prospect.company or '-'})")
            typer.echo(f"angle:   {m.angle or '-'}")
            typer.echo(f"subject: {m.subject or '-'}")
            typer.echo("")
            typer.echo(m.body)
        typer.echo("─" * 72)
        typer.echo(f"{len(drafts)} draft(s). Approve with: azul approve --campaign {c.id} --all")


@app.command("approve")
def approve(
    campaign: str = typer.Option(..., help="Campaign id or name"),
    message: list[str] = typer.Option([], "--message", help="Message id(s) to approve"),
    all_: bool = typer.Option(False, "--all", help="Approve every draft"),
    by: str = typer.Option("cli", help="Who approved"),
) -> None:
    """Approve drafts (the human tap). Use --all or one/more --message ids."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        ids = [uuid.UUID(m) for m in message] if message else None
        count = camp.approve(
            session, campaign_id=c.id, message_ids=ids, approve_all=all_, approved_by=by
        )
    typer.echo(f"Approved {count} message(s).")


@app.command("send-approved")
def send_approved(
    campaign: str = typer.Option(..., help="Campaign id or name"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Don't actually send"),
) -> None:
    """Send approved messages from the real mailbox (paced, idempotent)."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        sent = camp.send_approved(session, campaign_id=c.id, dry_run=dry_run)
    typer.echo(f"{'Would send' if dry_run else 'Sent'} {sent} message(s).")


@app.command("simulate-replies")
def simulate_replies(campaign: str = typer.Option(..., help="Campaign id or name")) -> None:
    """Stub-only: synthesize deterministic outcomes so `report` shows a real number."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        n = camp.simulate_replies(session, campaign_id=c.id)
    typer.echo(f"Recorded {n} simulated outcome(s).")


@app.command("report")
def report(campaign: str = typer.Option(..., help="Campaign id or name")) -> None:
    """The number that matters: reply rate (+ sentiment, meetings, bounces)."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        r = camp.build_report(session, campaign_id=c.id)
    typer.echo(f"Campaign:   {r.campaign}")
    typer.echo(f"Prospects:  {r.prospects}")
    typer.echo(f"Drafted:    {r.drafted}")
    typer.echo(f"Sent:       {r.sent}")
    typer.echo(f"Failed:     {r.failed}")
    typer.echo(f"Replied:    {r.replied}")
    typer.echo(f"Meetings:   {r.meetings}")
    typer.echo(f"Bounced:    {r.bounced}  ({r.bounce_rate:.0%})")
    typer.echo(f"Sentiment:  {r.sentiments or '-'}")
    typer.echo(f"REPLY RATE: {r.reply_rate:.0%}")


@app.command("auth-email")
def auth_email() -> None:
    """One-time Microsoft consent (device code) to send/read from your Outlook box."""
    from azul.connectors.graph_auth import device_code_login

    device_code_login()
    typer.echo("Email auth complete; token cached.")


@app.command("sync-replies")
def sync_replies(
    since_hours: int = typer.Option(168, help="Look back this many hours"),
) -> None:
    """Poll the mailbox for replies/bounces and record outcomes."""
    from datetime import UTC, datetime, timedelta

    from azul.connectors import get_channel
    from azul.memory import EpisodicMemory

    since = datetime.now(UTC) - timedelta(hours=since_hours)
    replies = get_channel().fetch_replies(since)
    with session_scope() as session:
        mem = EpisodicMemory(session)
        recorded = sum(1 for r in replies if mem.ingest_reply(r) is not None)
    typer.echo(f"Fetched {len(replies)} inbound, recorded {recorded} outcome(s).")


@app.command("linkedin-login")
def linkedin_login() -> None:
    """Open a browser to log into LinkedIn once; saves the session for Holo research."""
    from playwright.sync_api import sync_playwright

    path = get_settings().linkedin_storage_state or ".linkedin_state.json"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        ctx = browser.new_context()
        ctx.new_page().goto("https://www.linkedin.com/login")
        input("Log in to LinkedIn, then press Enter here to save the session... ")
        ctx.storage_state(path=path)
        browser.close()
    typer.echo(f"Saved LinkedIn session to {path}")


@app.command("doctor")
def doctor() -> None:
    """Preflight: check selected adapters, keys, and files before a real run."""
    from pathlib import Path

    s = get_settings()
    typer.echo(f"DB: {s.database_url}")
    typer.echo(
        f"adapters: sourcing={s.sourcing_provider} research={s.research_engine} "
        f"writer={s.writer_provider} channel={s.channel}"
    )
    checks: list[tuple[str, bool]] = []
    if s.sourcing_provider == "prospeo":
        checks.append(("PROSPEO_API_KEY", bool(s.prospeo_api_key)))
    if s.research_engine == "holo3":
        import importlib.util

        checks.append(("HAI_API_KEY", bool(s.hai_api_key)))
        checks.append(
            ("playwright installed", importlib.util.find_spec("playwright") is not None)
        )
        if s.linkedin_storage_state:
            checks.append(
                (f"LinkedIn session ({s.linkedin_storage_state})",
                 Path(s.linkedin_storage_state).exists())
            )
    if s.writer_provider == "openai_compat":
        checks.append(("WRITER_BASE_URL", bool(s.writer_base_url)))
        checks.append(("WRITER_MODEL", bool(s.writer_model)))
        checks.append(("WRITER_API_KEY", bool(s.writer_api_key)))
        checks.append(
            (f"playbook ({s.writer_playbook_path})", Path(s.writer_playbook_path).exists())
        )
    if s.channel == "graph":
        checks.append(("GRAPH_CLIENT_ID", bool(s.graph_client_id)))
        checks.append(
            (f"Graph token cached ({s.graph_token_cache})", Path(s.graph_token_cache).exists())
        )
    for label, good in checks:
        typer.echo(f"  {'OK ' if good else 'MISSING'} {label}")
    missing = [label for label, good in checks if not good]
    typer.echo(
        f"\n{len(missing)} item(s) need attention." if missing else "\nAll preflight checks passed."
    )


if __name__ == "__main__":
    app()
