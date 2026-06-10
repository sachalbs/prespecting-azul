"""Live preflight checks: real calls so a green doctor means a runnable pipeline.

Each check returns OK/FAIL plus a one-line remedy. Static env checks live in the
`doctor` CLI command; this module is the part that actually talks to the world
(DB, Tavily, writer, Holo, Graph, sender-domain SPF/DKIM/DMARC).
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

import dns.exception
import dns.resolver
import httpx
from sqlalchemy import inspect, text

from azul.config import Settings
from azul.logging import get_logger

log = get_logger(__name__)

_TIMEOUT = 10.0


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""  # remedy when failed, context when ok


# ── DB ───────────────────────────────────────────────────────────────────────


def check_db(settings: Settings) -> Check:
    from azul.db.session import get_engine

    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        has_messages = inspect(engine).has_table("messages")
    except Exception as exc:
        return Check("DB", False, f"can't connect to {settings.database_url}: {exc}")
    if not has_messages:
        return Check("DB", False, "schema missing — run `azul init-db` (or alembic upgrade head)")
    return Check("DB", True, settings.database_url)


# ── Tavily ───────────────────────────────────────────────────────────────────


def check_tavily(settings: Settings) -> Check:
    if not settings.tavily_api_key:
        return Check("Tavily", False, "set TAVILY_API_KEY (app.tavily.com)")
    try:
        resp = httpx.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {settings.tavily_api_key}"},
            json={"query": "azul healthcheck", "search_depth": "basic", "max_results": 1},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        return Check("Tavily", False, f"search returned {code} — check the key/plan")
    except httpx.HTTPError as exc:
        return Check("Tavily", False, f"network error: {type(exc).__name__}")
    return Check("Tavily", True, "search OK")


# ── Writer (OpenAI-compatible) ───────────────────────────────────────────────


def _one_token_completion(base_url: str, api_key: str, model: str) -> str | None:
    """None when the call works; a one-line remedy otherwise."""
    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 1,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code in (401, 403):
            return f"{code} — API key rejected"
        if code == 404:
            return f"404 — model '{model}' not found at {base_url}"
        return f"completion returned {code}"
    except httpx.HTTPError as exc:
        return f"network error: {type(exc).__name__}"
    return None


def check_writer(settings: Settings) -> Check:
    if not (settings.writer_base_url and settings.writer_api_key and settings.writer_model):
        return Check("Writer", False, "set WRITER_BASE_URL / WRITER_MODEL / WRITER_API_KEY")
    remedy = _one_token_completion(
        str(settings.writer_base_url), str(settings.writer_api_key), settings.writer_model
    )
    if remedy:
        return Check("Writer", False, remedy)
    return Check("Writer", True, f"{settings.writer_model} responds")


def check_holo(settings: Settings) -> Check:
    if not settings.hai_api_key:
        return Check("Holo", False, "set HAI_API_KEY (hcompany.ai)")
    remedy = _one_token_completion(
        settings.holo_base_url, settings.hai_api_key, settings.holo_model
    )
    if remedy:
        return Check("Holo", False, remedy)
    return Check("Holo", True, f"{settings.holo_model} responds")


# ── Microsoft Graph (Outlook) ────────────────────────────────────────────────


def _token_scopes(token: str) -> list[str]:
    """Scopes from the JWT 'scp' claim; [] when the token isn't decodable."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload))
        return str(data.get("scp", "")).split()
    except Exception:
        return []


def _acquire_token() -> str:
    from azul.connectors.graph_auth import acquire_token_silent

    return acquire_token_silent()


def check_graph(settings: Settings) -> tuple[list[Check], str | None]:
    """Graph checks + the connected mailbox's domain (for the DNS auth checks)."""
    from azul.errors import AzulError

    try:
        token = _acquire_token()
    except AzulError as exc:
        return [Check("Graph token", False, f"{exc} — run `azul auth-email`")], None

    try:
        resp = httpx.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        me = resp.json()
    except httpx.HTTPError as exc:
        remedy = f"{type(exc).__name__} — token may be stale, re-run `azul auth-email`"
        return [Check("Graph /me", False, remedy)], None

    email = str(me.get("mail") or me.get("userPrincipalName") or "")
    checks = [Check("Graph /me", True, email or "connected")]

    scopes = _token_scopes(token)
    if scopes and "Mail.Send" not in scopes:
        checks.append(
            Check("Mail.Send scope", False, "consent lacks Mail.Send — re-run `azul auth-email`")
        )
    elif scopes:
        checks.append(Check("Mail.Send scope", True, " ".join(scopes)))
    else:
        checks.append(Check("Mail.Send scope", True, "token opaque — verified at first send"))
    domain = email.split("@", 1)[1].lower() if "@" in email else None
    return checks, domain


# ── Sender-domain DNS auth (SPF / DKIM / DMARC), in human language ──────────


def _txt_records(name: str) -> list[str]:
    try:
        answers = dns.resolver.resolve(name, "TXT")
        return ["".join(s.decode() for s in r.strings) for r in answers]  # type: ignore[attr-defined]
    except dns.exception.DNSException:
        return []


def _name_exists(name: str) -> bool:
    for rtype in ("CNAME", "TXT"):
        try:
            dns.resolver.resolve(name, rtype)
            return True
        except dns.exception.DNSException:
            continue
    return False


def check_dns_auth(domain: str) -> list[Check]:
    checks: list[Check] = []

    spf = next((r for r in _txt_records(domain) if r.lower().startswith("v=spf1")), None)
    if spf:
        checks.append(
            Check("SPF", True, f"the world knows who may send for {domain}: '{spf[:80]}'")
        )
    else:
        checks.append(
            Check(
                "SPF", False,
                f"no SPF on {domain} — receivers can't trust your mail; add a TXT "
                "'v=spf1 include:spf.protection.outlook.com -all'",
            )
        )

    selectors = ("selector1", "selector2", "s1", "s2", "default")
    found = next((s for s in selectors if _name_exists(f"{s}._domainkey.{domain}")), None)
    if found:
        checks.append(Check("DKIM", True, f"signing key published ({found}._domainkey.{domain})"))
    else:
        checks.append(
            Check(
                "DKIM", False,
                f"no DKIM selector found on {domain} — messages aren't signed; "
                "enable DKIM in your mail provider and publish the selector records",
            )
        )

    dmarc = next(
        (r for r in _txt_records(f"_dmarc.{domain}") if r.lower().startswith("v=dmarc1")), None
    )
    if dmarc:
        checks.append(Check("DMARC", True, f"policy published: '{dmarc[:80]}'"))
    else:
        checks.append(
            Check(
                "DMARC", False,
                f"no DMARC on _dmarc.{domain} — add a TXT 'v=DMARC1; p=none; "
                f"rua=mailto:you@{domain}' to see who spoofs you and improve inboxing",
            )
        )
    return checks


# ── Orchestration ────────────────────────────────────────────────────────────


def run_live_checks(settings: Settings, domain: str | None = None) -> list[Check]:
    checks: list[Check] = [check_db(settings)]
    if settings.research_engine in ("tavily", "tiered"):
        checks.append(check_tavily(settings))
    if settings.writer_provider == "openai_compat":
        checks.append(check_writer(settings))
    if settings.research_engine in ("holo3", "tiered"):
        checks.append(check_holo(settings))
    send_domain = domain
    if settings.channel == "graph":
        graph_checks, mailbox_domain = check_graph(settings)
        checks.extend(graph_checks)
        send_domain = send_domain or mailbox_domain
    if send_domain:
        checks.extend(check_dns_auth(send_domain))
    return checks
