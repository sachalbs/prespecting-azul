"""Reply webhook receiver: provider events -> normalised replies -> outcomes.

Run with: uvicorn azul.api.webhooks:app
Point your Unipile (or provider) reply/bounce webhook at POST /webhooks/replies.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from azul.config import get_settings
from azul.connectors import get_channel
from azul.db.session import session_scope
from azul.logging import configure_logging, get_logger
from azul.memory import EpisodicMemory

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    s = get_settings()
    configure_logging(level=s.log_level, json=s.log_json)
    yield


app = FastAPI(title="Azul webhooks", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhooks/replies")
async def replies(
    request: Request, x_webhook_secret: str | None = Header(default=None)
) -> dict[str, Any]:
    settings = get_settings()
    if settings.unipile_webhook_secret and x_webhook_secret != settings.unipile_webhook_secret:
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
