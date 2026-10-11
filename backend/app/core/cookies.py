"""HttpOnly auth cookies — defense-in-depth alongside the existing bearer
token flow (see app/middleware/jwt_auth.py and app/api/auth/routes.py).

Why cookies in addition to the JSON body tokens: the response body tokens
remain for API/bearer clients (mobile apps, server-to-server, the existing
frontend flow), but a browser session that also receives these cookies is
protected even if an XSS bug leaks/tampers with JS-accessible storage —
httpOnly means client-side JS can never read or exfiltrate them, and
SameSite=Lax stops them being sent on cross-site requests.
"""
from __future__ import annotations

import os

from fastapi import Response

from app.core.config import settings

ACCESS_COOKIE_NAME = "oraone_access_token"
REFRESH_COOKIE_NAME = "oraone_refresh_token"


def _is_production() -> bool:
    return os.environ.get("ENVIRONMENT", "").strip().lower() in ("production", "prod", "staging")


def _secure_flag() -> bool:
    # Secure cookies are dropped by browsers over plain HTTP — only enforce
    # in prod/staging where the app is always served over HTTPS (Caddy).
    return _is_production()


def set_auth_cookies(response: Response, *, access_token: str, refresh_token: str | None) -> None:
    response.set_cookie(
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.jwt_access_ttl_minutes * 60,
        httponly=True,
        secure=_secure_flag(),
        samesite="lax",
        path="/",
    )
    if refresh_token:
        response.set_cookie(
            key=REFRESH_COOKIE_NAME,
            value=refresh_token,
            max_age=settings.jwt_refresh_ttl_days * 86400,
            httponly=True,
            secure=_secure_flag(),
            samesite="lax",
            # Narrow scope — only sent to auth endpoints, minimizing exposure
            # of the long-lived, more sensitive token.
            path="/api/auth",
        )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth")
