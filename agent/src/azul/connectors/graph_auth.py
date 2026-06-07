"""Microsoft Graph (Outlook) token acquisition via MSAL device-code flow.

Delegated scopes: Mail.Send + Mail.Read + User.Read (offline_access is added by
MSAL for the refresh token). `azul auth-email` runs the one-time device-code
consent; tokens are cached so later sends/polls are silent.
"""

from __future__ import annotations

from pathlib import Path

import msal

from azul.config import get_settings
from azul.errors import ChannelError, ConfigError

SCOPES = ["Mail.Send", "Mail.Read", "User.Read"]


def _build_app() -> tuple[msal.PublicClientApplication, msal.SerializableTokenCache, Path]:
    s = get_settings()
    if not s.graph_client_id:
        raise ConfigError("GRAPH_CLIENT_ID is required for CHANNEL=graph")
    cache = msal.SerializableTokenCache()
    path = Path(s.graph_token_cache)
    if path.exists():
        cache.deserialize(path.read_text())
    app = msal.PublicClientApplication(
        s.graph_client_id, authority=s.graph_authority, token_cache=cache
    )
    return app, cache, path


def _persist(cache: msal.SerializableTokenCache, path: Path) -> None:
    if cache.has_state_changed:
        path.write_text(cache.serialize())


def acquire_token_silent() -> str:
    """Return a cached/refreshed access token, or fail telling the user to log in."""
    app, cache, path = _build_app()
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _persist(cache, path)
            return str(result["access_token"])
    raise ChannelError("No cached Graph token — run `azul auth-email` first")


def device_code_login() -> str:
    """Interactive one-time consent. Prints a URL + code; blocks until completed."""
    app, cache, path = _build_app()
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise ChannelError(f"Failed to start device flow: {flow}")
    print(flow["message"], flush=True)  # noqa: T201 — instructs the user
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise ChannelError(f"Auth failed: {result.get('error_description', result)}")
    _persist(cache, path)
    return str(result["access_token"])
