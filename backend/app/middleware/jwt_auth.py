"""Bearer-token verification for self-hosted migration and Cognito production.

Every 401 from this module is logged with a precise reason at WARNING
level under the logger `app.auth.jwt`. Tail uvicorn output to see them.
"""

import logging
import json
import time
from typing import Any, Dict

from fastapi import HTTPException, Request, status
import httpx
import jwt as jose_jwt
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import InvalidTokenError as JWTError

from app.core.config import settings
from app.core.security import decode_access_token

log = logging.getLogger("app.auth.jwt")
_jwks_cache: dict[str, Any] = {"expires_at": 0.0, "keys": []}


def _unauthorized(reason: str, *, request: Request | None = None) -> HTTPException:
    """Log the *real* reason then raise the generic 401."""
    path = request.url.path if request is not None else "?"
    log.warning("AUTH 401 path=%s reason=%s", path, reason)
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def verify_access_token(token: str, request: Request | None = None) -> Dict[str, Any]:
    """Verify a self-issued access token and return its claims."""
    try:
        claims = decode_access_token(token)
    except JWTError as e:
        raise _unauthorized(f"invalid_token: {type(e).__name__}: {e}", request=request)

    log.info(
        "AUTH OK sub=%s path=%s",
        claims.get("sub"),
        request.url.path if request else "?",
    )
    return claims


async def verify_cognito_access_token(
    token: str, request: Request | None = None, *, _refreshed: bool = False
) -> Dict[str, Any]:
    """Verify a Cognito access token using the pool's rotating JWKS keys.

    Cognito access tokens use ``client_id`` rather than ``aud``.  The
    verifier therefore validates issuer, expiry, access-token ``token_use``,
    and client id explicitly instead of accepting an arbitrary JWT.
    """
    try:
        header = jose_jwt.get_unverified_header(token)
        kid = header.get("kid")
        alg = header.get("alg")
        if not kid or alg != "RS256":
            raise JWTError("unexpected JWT header")

        now = time.time()
        if now >= float(_jwks_cache["expires_at"]):
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(settings.cognito_jwks_url)
                response.raise_for_status()
                payload = response.json()
            keys = payload.get("keys", [])
            if not keys:
                raise JWTError("Cognito JWKS contained no keys")
            _jwks_cache.update({"keys": keys, "expires_at": now + 3600})

        key = next(
            (item for item in _jwks_cache["keys"] if item.get("kid") == kid), None
        )
        if key is None:
            # A rotation may have happened; refresh once before rejecting.
            _jwks_cache["expires_at"] = 0
            if _refreshed:
                raise JWTError("Cognito JWKS does not contain token key")
            return await verify_cognito_access_token(
                token, request=request, _refreshed=True
            )

        verification_key = (
            RSAAlgorithm.from_jwk(json.dumps(key))
            if key.get("n") and key.get("e")
            else key
        )
        claims = jose_jwt.decode(
            token,
            verification_key,
            algorithms=["RS256"],
            issuer=settings.cognito_token_issuer,
            options={"verify_aud": False},
            leeway=60,
        )
        if claims.get("token_use") != "access":
            raise JWTError("Cognito token_use must be access")
        if claims.get("client_id") != settings.cognito_client_id:
            raise JWTError("Cognito client_id mismatch")
    except (JWTError, httpx.HTTPError, ValueError, KeyError) as exc:
        raise _unauthorized(
            f"invalid_cognito_token: {type(exc).__name__}", request=request
        )

    log.info(
        "AUTH OK provider=cognito sub=%s path=%s",
        claims.get("sub"),
        request.url.path if request else "?",
    )
    return claims


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if not auth_header:
        # Browser sessions may rely on the httpOnly access-token cookie instead
        # of an Authorization header (see app/core/cookies.py).
        from app.core.cookies import ACCESS_COOKIE_NAME

        cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
        if cookie_token:
            return cookie_token
        # Show all header names received (not values — could be sensitive) so
        # we can spot proxies that strip "Authorization".
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
    """FastAPI dependency: validates the Bearer token and returns its claims."""
    token = _extract_bearer_token(request)
    if settings.auth_provider == "cognito":
        return await verify_cognito_access_token(token, request=request)
    return verify_access_token(token, request=request)


async def get_current_access_token(request: Request) -> str:
    """FastAPI dependency that returns the validated raw access token."""
    token = _extract_bearer_token(request)
    if settings.auth_provider == "cognito":
        await verify_cognito_access_token(token, request=request)
    else:
        verify_access_token(token, request=request)
    return token
