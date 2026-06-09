"""Reply webhook receiver: provider events -> normalised replies -> outcomes.

Run with: uvicorn azul.api.webhooks:app
Point your Unipile (or provider) reply/bounce webhook at POST /webhooks/replies.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from azul.config import get_settings
from azul.connectors import get_channel
from azul.connectors.accounts import store_outlook_account
from azul.connectors.graph_auth import authorization_url, exchange_code
from azul.db.session import session_scope
from azul.logging import configure_logging, get_logger
from azul.memory import EpisodicMemory
from azul.orchestrator.campaign import ensure_tenant

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    s = get_settings()
    configure_logging(level=s.log_level, json=s.log_json)
    yield


app = FastAPI(title="Azul API", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/oauth/outlook/start")
def oauth_outlook_start(tenant: str) -> RedirectResponse:
    """Send the user to Microsoft consent; `state` carries their tenant."""
    return RedirectResponse(authorization_url(state=tenant))


@app.get("/oauth/outlook/callback", response_class=HTMLResponse)
def oauth_outlook_callback(code: str, state: str) -> str:
    """Store the tenant's Outlook refresh token, then send them back to chat."""
    refresh_token, email = exchange_code(code)
    with session_scope() as session:
        tenant = ensure_tenant(session, state)
        store_outlook_account(session, tenant.id, refresh_token, email)
    log.info("outlook_connected", tenant=state, email=email)
    return (
        "<h2>Outlook connecté ✅</h2>"
        "<p>Reviens sur ton chat Azul — ton essai peut commencer.</p>"
    )


@app.post("/webhooks/replies")
async def replies(
    request: Request, x_webhook_secret: str | None = Header(default=None)
) -> dict[str, Any]:
    settings = get_settings()
    if settings.webhook_secret and x_webhook_secret != settings.webhook_secret:
        raise HTTPException(status_code=401, detail="bad webhook secret")

    payload: dict[str, Any] = await request.json()
    inbound = get_channel().parse_webhook(payload)
    recorded = 0
    with session_scope() as session:
        mem = EpisodicMemory(session)
        for reply in inbound:
            if mem.ingest_reply(reply) is not None:
                recorded += 1
    log.info("webhook_processed", events=len(inbound), recorded=recorded)
    return {"received": len(inbound), "recorded": recorded}
