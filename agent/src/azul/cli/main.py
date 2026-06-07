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


if __name__ == "__main__":
    app()
