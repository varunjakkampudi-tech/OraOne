"""OAuth service (Phase 10).

Generic OAuth2 authorization-code helper. Provider endpoints + scopes
live in :data:`_OAUTH_PROVIDERS`; client credentials come from env vars
(e.g. ``GOOGLE_CLIENT_ID`` / ``GOOGLE_CLIENT_SECRET`` /
``GOOGLE_REDIRECT_URI``). When a provider has no configured client
secret, :func:`is_configured` returns False and the API connects the
integration in *mock* mode instead — so local dev never needs real
secrets.

Tokens are returned in plaintext here; the caller encrypts them before
persisting (see ``app.core.crypto``).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.connectors.base import ConnectResult, OAuthError

log = logging.getLogger("app.oauth")


_OAUTH_PROVIDERS: dict[str, dict[str, Any]] = {
    "google_drive": {
        "env_prefix": "GOOGLE",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        # Read the signed-in account straight from the Drive API so we don't
        # need an extra userinfo/email scope — keeps consent to drive.readonly.
        "userinfo_url": "https://www.googleapis.com/drive/v3/about?fields=user",
        "scopes": [
            "https://www.googleapis.com/auth/drive.readonly",
        ],
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
    },
}


def _cfg(provider: str) -> Optional[dict[str, Any]]:
    return _OAUTH_PROVIDERS.get(provider)


def _client_id(prefix: str) -> Optional[str]:
    return os.environ.get(f"{prefix}_CLIENT_ID")


def _client_secret(prefix: str) -> Optional[str]:
    return os.environ.get(f"{prefix}_CLIENT_SECRET")


def _redirect_uri(prefix: str) -> str:
    return os.environ.get(
        f"{prefix}_REDIRECT_URI",
        "http://localhost:3000/api/integrations/google/callback",
    )


def is_configured(provider: str) -> bool:
    """True if this provider has real OAuth client credentials in env."""
    cfg = _cfg(provider)
    if cfg is None:
        return False
    prefix = cfg["env_prefix"]
    return bool(_client_id(prefix) and _client_secret(prefix))


def build_authorize_url(provider: str, *, state: str) -> str:
    cfg = _cfg(provider)
    if cfg is None or not is_configured(provider):
        raise OAuthError(f"OAuth is not configured for provider {provider!r}.")
    prefix = cfg["env_prefix"]
    params = {
        "client_id": _client_id(prefix),
        "redirect_uri": _redirect_uri(prefix),
        "response_type": "code",
        "scope": " ".join(cfg["scopes"]),
        "state": state,
        **cfg.get("extra_auth_params", {}),
    }
    return f"{cfg['auth_url']}?{urlencode(params)}"


def complete_connect(provider: str, *, code: Optional[str] = None, **kwargs: Any) -> ConnectResult:
    """Exchange an authorization code for tokens (real OAuth providers)."""
    cfg = _cfg(provider)
    if cfg is None or not is_configured(provider):
        raise OAuthError(f"OAuth is not configured for provider {provider!r}.")
    if not code:
        raise OAuthError("Missing authorization code.")

    prefix = cfg["env_prefix"]
    data = {
        "code": code,
        "client_id": _client_id(prefix),
        "client_secret": _client_secret(prefix),
        "redirect_uri": _redirect_uri(prefix),
        "grant_type": "authorization_code",
    }
    try:
        r = httpx.post(cfg["token_url"], data=data, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise OAuthError(f"Token exchange failed: {e}") from e

    payload = r.json()
    expires_at = _expiry(payload.get("expires_in"))
    account = _fetch_account(cfg, payload.get("access_token"))
    return ConnectResult(
        access_token=payload.get("access_token"),
        refresh_token=payload.get("refresh_token"),
        token_expires_at=expires_at,
        external_account=account,
        config={},
    )


def refresh(provider: str, *, refresh_token: str) -> ConnectResult:
    cfg = _cfg(provider)
    if cfg is None or not is_configured(provider):
        raise OAuthError(f"OAuth is not configured for provider {provider!r}.")
    prefix = cfg["env_prefix"]
    data = {
        "refresh_token": refresh_token,
        "client_id": _client_id(prefix),
        "client_secret": _client_secret(prefix),
        "grant_type": "refresh_token",
    }
    try:
        r = httpx.post(cfg["token_url"], data=data, timeout=30)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise OAuthError(f"Token refresh failed: {e}") from e

    payload = r.json()
    return ConnectResult(
        access_token=payload.get("access_token"),
        # Google may not return a new refresh token; keep the old one.
        refresh_token=payload.get("refresh_token"),
        token_expires_at=_expiry(payload.get("expires_in")),
    )


def _expiry(expires_in: Any) -> Optional[datetime]:
    try:
        seconds = int(expires_in)
    except (TypeError, ValueError):
        return None
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _fetch_account(cfg: dict[str, Any], access_token: Optional[str]) -> Optional[str]:
    url = cfg.get("userinfo_url")
    if not url or not access_token:
        return None
    try:
        r = httpx.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Drive's /about returns {"user": {"emailAddress", "displayName"}};
            # classic userinfo returns {"email", "name"}.
            user = data.get("user")
            if isinstance(user, dict):
                return user.get("emailAddress") or user.get("displayName")
            return data.get("email") or data.get("name")
    except httpx.HTTPError:
        pass
    return None
