"""OAuth service (Phase 10).

Generic OAuth2 authorization-code helper. Provider endpoints + scopes
live in :data:`_OAUTH_PROVIDERS`; client credentials come from env vars named
``{env_prefix}_CLIENT_ID`` / ``{env_prefix}_CLIENT_SECRET`` (optionally
``{env_prefix}_REDIRECT_URI``), e.g. ``GOOGLE_CLIENT_ID`` for Google Drive or
``GOOGLE_CALENDAR_CLIENT_ID`` for Google Calendar. When credentials are missing,
:func:`is_configured` returns False and connection fails closed.

This module builds the authorization URL and performs the token exchange only.
It never calls provider data APIs; sync actions for the newer providers are
planned and not implemented.

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

# Shared browser callback for providers added after Google Drive. The Google Drive
# callback path is kept unchanged because it is already registered with Google.
GENERIC_CALLBACK_PATH = "/api/integrations/oauth/callback"
_LEGACY_GOOGLE_CALLBACK_PATH = "/api/integrations/google/callback"


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
        "callback_path": _LEGACY_GOOGLE_CALLBACK_PATH,
    },
    "google_calendar": {
        "env_prefix": "GOOGLE_CALENDAR",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": None,
        "scopes": ["https://www.googleapis.com/auth/calendar.events"],
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "token_auth": "body",
        "callback_path": GENERIC_CALLBACK_PATH,
    },
    "google_sheets": {
        "env_prefix": "GOOGLE_SHEETS",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": None,
        "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
        "extra_auth_params": {"access_type": "offline", "prompt": "consent"},
        "token_auth": "body",
        "callback_path": GENERIC_CALLBACK_PATH,
    },
    "slack": {
        "env_prefix": "SLACK",
        "auth_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
        "userinfo_url": None,
        "scopes": ["chat:write"],
        "extra_auth_params": {},
        "token_auth": "body",
        "callback_path": GENERIC_CALLBACK_PATH,
    },
    "hubspot": {
        "env_prefix": "HUBSPOT",
        "auth_url": "https://app.hubspot.com/oauth/authorize",
        "token_url": "https://api.hubapi.com/oauth/v1/token",
        "userinfo_url": None,
        "scopes": [
            "crm.objects.contacts.read",
            "crm.objects.contacts.write",
        ],
        "extra_auth_params": {},
        "token_auth": "body",
        "callback_path": GENERIC_CALLBACK_PATH,
    },
    "notion": {
        "env_prefix": "NOTION",
        "auth_url": "https://api.notion.com/v1/oauth/authorize",
        "token_url": "https://api.notion.com/v1/oauth/token",
        "userinfo_url": None,
        # Notion takes no scope list; the owner type is what it asks for.
        "scopes": [],
        "extra_auth_params": {"owner": "user"},
        "token_auth": "basic",
        "callback_path": GENERIC_CALLBACK_PATH,
    },
}


def _cfg(provider: str) -> Optional[dict[str, Any]]:
    return _OAUTH_PROVIDERS.get(provider)


def _client_id(prefix: str) -> Optional[str]:
    return os.environ.get(f"{prefix}_CLIENT_ID")


def _client_secret(prefix: str) -> Optional[str]:
    return os.environ.get(f"{prefix}_CLIENT_SECRET")


def _redirect_uri(cfg: dict[str, Any]) -> str:
    prefix = cfg["env_prefix"]
    return os.environ.get(
        f"{prefix}_REDIRECT_URI",
        "http://localhost:3000"
        + cfg.get("callback_path", _LEGACY_GOOGLE_CALLBACK_PATH),
    )


def required_settings(provider: str) -> list[str]:
    """Names (never values) of the server settings a provider needs."""
    cfg = _cfg(provider)
    if cfg is None:
        return []
    prefix = cfg["env_prefix"]
    return [f"{prefix}_CLIENT_ID", f"{prefix}_CLIENT_SECRET"]


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
    params: dict[str, Any] = {
        "client_id": _client_id(prefix),
        "redirect_uri": _redirect_uri(cfg),
        "response_type": "code",
        "state": state,
        **cfg.get("extra_auth_params", {}),
    }
    if cfg["scopes"]:
        params["scope"] = " ".join(cfg["scopes"])
    return f"{cfg['auth_url']}?{urlencode(params)}"


def _post_token(cfg: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    """POST to the provider token endpoint; return the decoded JSON body."""
    prefix = cfg["env_prefix"]
    client_id = _client_id(prefix)
    client_secret = _client_secret(prefix)
    auth = None
    body = dict(data)
    if cfg.get("token_auth") == "basic":
        auth = (client_id or "", client_secret or "")
    else:
        body["client_id"] = client_id
        body["client_secret"] = client_secret
    try:
        r = httpx.post(cfg["token_url"], data=body, auth=auth, timeout=30)
        r.raise_for_status()
        payload = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise OAuthError(f"Token request failed: {e}") from e
    if not isinstance(payload, dict):
        raise OAuthError("Token response was not a JSON object.")
    # Slack reports failures as HTTP 200 with ok=false.
    if payload.get("ok") is False:
        raise OAuthError(f"Provider rejected the token request: {payload.get('error')}")
    return payload


def complete_connect(
    provider: str, *, code: Optional[str] = None, **kwargs: Any
) -> ConnectResult:
    """Exchange an authorization code for tokens (real OAuth providers)."""
    cfg = _cfg(provider)
    if cfg is None or not is_configured(provider):
        raise OAuthError(f"OAuth is not configured for provider {provider!r}.")
    if not code:
        raise OAuthError("Missing authorization code.")

    payload = _post_token(
        cfg,
        {
            "code": code,
            "redirect_uri": _redirect_uri(cfg),
            "grant_type": "authorization_code",
        },
    )
    if not payload.get("access_token"):
        raise OAuthError("Token exchange returned no access token.")

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
    payload = _post_token(
        cfg,
        {"refresh_token": refresh_token, "grant_type": "refresh_token"},
    )
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
        r = httpx.get(
            url, headers={"Authorization": f"Bearer {access_token}"}, timeout=15
        )
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
