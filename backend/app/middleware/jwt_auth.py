"""Bearer-token verification for OraOne's self-hosted sessions.

Access tokens are issued by :mod:`app.services.token_service` and may arrive
either as an ``Authorization: Bearer`` header or in the httpOnly access-token
cookie set at sign-in. Every rejected request is logged with its precise reason
under the ``app.auth.jwt`` logger, while the client only receives a generic 401.
"""

import logging
from typing import Any, Dict

from fastapi import HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.security import decode_access_token

log = logging.getLogger("app.auth.jwt")


def _unauthorized(reason: str, *, request: Request | None = None) -> HTTPException:
    """Log the real rejection reason and return the generic 401 to send."""
    path = request.url.path if request is not None else "?"
    log.warning("AUTH 401 path=%s reason=%s", path, reason)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_access_token(token: str, request: Request | None = None) -> Dict[str, Any]:
    """Verify a self-issued access token and return its claims.

    Raises a 401 HTTPException when the signature, expiry or issuer is invalid.
    """
    try:
        claims = decode_access_token(token)
    except InvalidTokenError as exc:
        raise _unauthorized(
            f"invalid_token: {type(exc).__name__}: {exc}", request=request
        ) from exc

    log.info(
        "AUTH OK sub=%s path=%s",
        claims.get("sub"),
        request.url.path if request else "?",
    )
    return claims


def _extract_bearer_token(request: Request) -> str:
    """Return the raw access token from the header or the session cookie."""
    auth_header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if not auth_header:
        # Browser sessions send the httpOnly cookie instead of a header.
        cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
        if cookie_token:
            return cookie_token
        # Log header names only (never values) to help diagnose stripped headers.
        names = sorted(request.headers.keys())
        raise _unauthorized(
            f"no_authorization_header_or_cookie (received headers: {names})",
            request=request,
        )
    if not auth_header.lower().startswith("bearer "):
        raise _unauthorized(
            f"authorization_not_bearer (prefix={auth_header[:20]!r})", request=request
        )
    token = auth_header[7:].strip()
    if not token:
        raise _unauthorized("empty_token_after_bearer", request=request)
    return token


async def get_current_user_claims(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: validate the access token and return its claims."""
    return verify_access_token(_extract_bearer_token(request), request=request)


async def get_current_access_token(request: Request) -> str:
    """FastAPI dependency: validate the access token and return the raw string."""
    token = _extract_bearer_token(request)
    verify_access_token(token, request=request)
    return token
