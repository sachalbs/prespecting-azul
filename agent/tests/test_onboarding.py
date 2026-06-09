"""Connect-Outlook-from-chat: OAuth endpoints (MSAL mocked) + the chat link."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

import azul.api.webhooks as webhooks
from azul.api.webhooks import app
from azul.cli.chat import ChatSession
from azul.connectors.accounts import get_outlook_account
from azul.db.models import Tenant
from azul.db.session import session_scope


def test_oauth_start_redirects_to_consent(monkeypatch: Any) -> None:
    def fake_auth_url(state: str) -> str:
        return f"https://login.test/auth?state={state}"

    monkeypatch.setattr(webhooks, "authorization_url", fake_auth_url)
    client = TestClient(app)
    r = client.get("/oauth/outlook/start", params={"tenant": "acme"}, follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "state=acme" in r.headers["location"]


def test_oauth_callback_stores_per_tenant_token(monkeypatch: Any) -> None:
    def fake_exchange(code: str) -> tuple[str, str | None]:
        return ("refresh-xyz", "ann@acme.com")

    monkeypatch.setattr(webhooks, "exchange_code", fake_exchange)
    client = TestClient(app)
    r = client.get("/oauth/outlook/callback", params={"code": "c", "state": "acme"})
    assert r.status_code == 200
    assert "connect" in r.text.lower()
    with session_scope() as s:
        tenant = s.scalars(select(Tenant).where(Tenant.slug == "acme")).first()
        assert tenant is not None
        acct = get_outlook_account(s, tenant.id)
        assert acct is not None
        assert acct.refresh_token == "refresh-xyz"
        assert acct.account_email == "ann@acme.com"


def test_chat_connect_returns_oauth_link() -> None:
    out = ChatSession(tenant="acme").handle("connect")
    assert "/oauth/outlook/start?tenant=acme" in out
