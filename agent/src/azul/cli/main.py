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


@app.command("discover")
def discover(
    tenant: str = typer.Option(..., help="Tenant slug"),
    n: int = typer.Option(25, help="How many prospects to aim for"),
    top: int | None = typer.Option(None, "--top", help="Non-interactive: keep the N best"),
    reuse_brief: bool = typer.Option(
        False, "--reuse-brief", help="Reuse the tenant's latest saved brief (skip questions)"
    ),
) -> None:
    """Conversational brief -> web discovery -> scored table -> YOU pick who gets in."""
    from datetime import UTC, datetime

    from azul.discovery.brief import BriefSession, load_latest_brief, save_brief
    from azul.discovery.dedup import dedupe
    from azul.discovery.icp_scorer import score_candidates
    from azul.discovery.store import promote, ranked, render_table, save_candidates
    from azul.discovery.web_discovery import WebDiscovery
    from azul.orchestrator.campaign import ensure_tenant

    # 1. The brief — conversational, or reused from the tenant's targeting memory.
    brief = None
    brief_row_id = None
    if reuse_brief:
        with session_scope() as s:
            t = ensure_tenant(s, tenant)
            brief = load_latest_brief(s, t.id)
        if brief is None:
            typer.echo("No saved brief for this tenant — let's build one.")
    if brief is None:
        bs = BriefSession()
        first = typer.prompt("Décris ce que tu vends et qui tu cherches")
        question = bs.start(first)
        while question is not None:
            question = bs.reply(typer.prompt(f"azul ▸ {question}\nyou"))
        brief = bs.brief
        assert brief is not None
        with session_scope() as s:
            t = ensure_tenant(s, tenant)
            brief_row_id = save_brief(s, t.id, brief).id
        typer.echo("Brief enregistré (mémoire de ciblage du tenant).")

    # 2. Discover -> dedup -> score -> persist everything (annotated, nothing dropped).
    typer.echo(f"Recherche en cours (vise ~{n} prospects, sur-échantillonné)...")
    candidates = WebDiscovery().discover(brief, n)
    with session_scope() as s:
        t = ensure_tenant(s, tenant)
        candidates = dedupe(s, t.id, candidates)
        score_candidates(brief, candidates)
        rows = save_candidates(s, t.id, candidates, brief_id=brief_row_id)
        table = render_table(rows)
        ordered_ids = [r.id for r in ranked(rows)]
    if not ordered_ids:
        typer.echo("Aucun candidat nouveau trouvé (tout était déjà connu ?).")
        return
    typer.echo(table)

    # 3. Explicit human selection — nothing enters the pipeline without it.
    if top is not None:
        picked_idx = list(range(1, min(top, len(ordered_ids)) + 1))
    else:
        raw = typer.prompt("Qui je retiens ? (ex: 1 3 5 · top 5 · rien)", default="rien")
        raw = raw.strip().lower()
        if raw in ("rien", "none", ""):
            typer.echo("OK — personne ne rentre dans le pipeline. Les candidats restent notés.")
            return
        if raw.startswith("top"):
            count = int(raw.split()[1]) if len(raw.split()) > 1 else 5
            picked_idx = list(range(1, min(count, len(ordered_ids)) + 1))
        else:
            picked_idx = [int(t) for t in raw.split() if t.isdigit()]
            picked_idx = [i for i in picked_idx if 1 <= i <= len(ordered_ids)]
    if not picked_idx:
        typer.echo("Sélection vide — personne ne rentre dans le pipeline.")
        return

    name = f"discover {datetime.now(UTC):%Y-%m-%d %H:%M}"
    with session_scope() as s:
        t = ensure_tenant(s, tenant)
        from azul.db.models import DiscoveryCandidate

        chosen = [s.get(DiscoveryCandidate, ordered_ids[i - 1]) for i in picked_idx]
        prospects, campaign = promote(
            s, t.id, [c for c in chosen if c is not None], campaign_name=name
        )
        cid = campaign.id
        count = len(prospects)
    typer.echo(f"\n{count} prospect(s) retenus (statut DISCOVERED, campagne {cid}).")
    typer.echo(f"Pipeline: azul approve-list --campaign {cid}")


@app.command("approve-list")
def approve_list_cmd(
    campaign: str = typer.Option(..., help="Campaign id or name"),
    sender: str | None = typer.Option(None, help="Sender name for the messages"),
    value_prop: str | None = typer.Option(None, help="One-line value prop"),
) -> None:
    """Run the pipeline (find email -> research -> draft) on a DISCOVERED campaign."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        drafted = camp.approve_list(
            session, campaign_id=c.id, sender_name=sender, value_prop=value_prop
        )
        cid = c.id
    typer.echo(f"{drafted} draft(s) ready. Next: azul review --campaign {cid}")


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


@app.command("redraft")
def redraft(
    campaign: str = typer.Option(..., help="Campaign id or name"),
    sender: str | None = typer.Option(None, help="Sender name for the messages"),
    value_prop: str | None = typer.Option(None, help="One-line value prop"),
) -> None:
    """Regenerate a campaign's drafts in place — no re-resolve, no re-find, no research."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        n = camp.redraft_campaign(
            session, campaign_id=c.id, sender_name=sender, value_prop=value_prop
        )
        cid = c.id
    typer.echo(f"Redrafted {n} draft(s). Next: azul review --campaign {cid}")


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


@app.command("learn")
def learn() -> None:
    """Run the flywheel curator: mine outcomes into procedural skills."""
    from azul.memory.flywheel import run_curator

    with session_scope() as session:
        n = run_curator(session)
    typer.echo(f"Curated {n} skill pattern(s) from outcomes.")


@app.command("follow-up")
def follow_up(campaign: str = typer.Option(..., help="Campaign id or name")) -> None:
    """Draft one follow-up for each prospect who hasn't replied (a child message)."""
    with session_scope() as session:
        c = camp.resolve_campaign(session, campaign)
        n = camp.generate_followups(session, campaign_id=c.id)
    typer.echo(f"Drafted {n} follow-up(s).")


@app.command("doctor")
def doctor(
    offline: bool = typer.Option(False, "--offline", help="Skip the live API calls"),
    domain: str | None = typer.Option(None, help="Sender domain for SPF/DKIM/DMARC checks"),
) -> None:
    """Preflight: env checks + REAL calls (DB, Tavily, writer, Holo, Graph, DNS auth)."""
    from pathlib import Path

    s = get_settings()
    typer.echo(f"DB: {s.database_url}")
    typer.echo(
        f"adapters: sourcing={s.sourcing_provider} research={s.research_engine} "
        f"writer={s.writer_provider} channel={s.channel}"
    )
    checks: list[tuple[str, bool]] = []
    if s.sourcing_provider == "finder":
        import importlib.util

        checks.append(("dnspython installed", importlib.util.find_spec("dns") is not None))
        if not s.verify_smtp:
            typer.echo(
                "  NOTE  VERIFY_SMTP=false — no SMTP handshake, verdicts cap at UNKNOWN "
                "(fine off-VPS; enable on the VPS where port 25 is open)"
            )
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

    failed_live = 0
    if not offline:
        from azul.cli.doctor import run_live_checks

        typer.echo("\nLive checks (real calls):")
        for check in run_live_checks(s, domain=domain):
            status = "OK  " if check.ok else "FAIL"
            typer.echo(f"  {status} {check.name}" + (f" — {check.detail}" if check.detail else ""))
            if not check.ok:
                failed_live += 1

    total = len(missing) + failed_live
    typer.echo(
        f"\n{total} item(s) need attention." if total else "\nAll preflight checks passed."
    )


@app.command("deliverability-check")
def deliverability_check(
    mail_tester: str = typer.Argument(..., help="The check-my-mail address from mail-tester.com"),
) -> None:
    """Send 1 REAL mail (Graph) to mail-tester + SEED_INBOXES; you read the verdicts."""
    from azul.cli.doctor import run_deliverability_check

    sent = run_deliverability_check(get_settings(), mail_tester)
    for to in sent:
        typer.echo(f"  sent -> {to}")
    typer.echo(
        f"\nSent {len(sent)} probe(s). Now read the mail-tester score and check "
        "inbox vs spam on each seed mailbox."
    )


@app.command("chat")
def chat() -> None:
    """Manage Azul like an employee, from chat (the product surface)."""
    from azul.cli.chat import run_chat

    run_chat()


@app.command("telegram-bot")
def telegram_bot() -> None:
    """Run Azul's Telegram operator bot (long-poll) — the chat surface over Telegram."""
    from azul.chatops.telegram import TelegramBot

    TelegramBot().poll()


if __name__ == "__main__":
    app()
