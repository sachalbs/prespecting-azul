"""Per-tenant connected accounts (OAuth tokens) → a ready-to-send Channel.

The onboarding stores a refresh token per tenant; sends mint an access token from
it. This is what makes Azul multi-tenant: each customer sends from their own box.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from azul.connectors.graph import GraphChannel
from azul.connectors.graph_auth import token_from_refresh
from azul.db.models import ConnectedAccount
from azul.errors import ChannelError


def store_outlook_account(
    session: Session, tenant_id: uuid.UUID, refresh_token: str, email: str | None = None
) -> ConnectedAccount:
    acct = session.scalars(
        select(ConnectedAccount).where(
            ConnectedAccount.tenant_id == tenant_id, ConnectedAccount.provider == "outlook"
        )
    ).first()
    if acct is None:
        acct = ConnectedAccount(
            tenant_id=tenant_id, provider="outlook", refresh_token=refresh_token,
            account_email=email,
        )
        session.add(acct)
    else:
        acct.refresh_token = refresh_token
        acct.account_email = email or acct.account_email
    session.flush()
    return acct


def get_outlook_account(session: Session, tenant_id: uuid.UUID) -> ConnectedAccount | None:
    return session.scalars(
        select(ConnectedAccount).where(
            ConnectedAccount.tenant_id == tenant_id, ConnectedAccount.provider == "outlook"
        )
    ).first()


def graph_for_tenant(session: Session, tenant_id: uuid.UUID) -> GraphChannel:
    """A GraphChannel authenticated as the tenant's connected Outlook mailbox."""
    acct = get_outlook_account(session, tenant_id)
    if acct is None:
        raise ChannelError("Outlook not connected for this tenant — run the connect flow")
    return GraphChannel(token=token_from_refresh(acct.refresh_token))
