"""Self-hosted authentication primitives — password hashing + JWT.

Replaces AWS Cognito. Two building blocks:

* :class:`PasswordHasher` (Argon2id via ``argon2-cffi``) — hash/verify.
* JWT helpers — HS256 access tokens signed with ``settings.jwt_secret_key``.
  Refresh tokens are *not* JWTs; they're opaque random strings tracked in
  Redis/cache (see ``app/services/token_service.py``) so they can be
  individually revoked and rotated, which a stateless JWT can't do.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from argon2 import PasswordHasher as _Argon2Hasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from jose import JWTError, jwt as jose_jwt

from app.core.config import settings

# ─────────────────────────── passwords ───────────────────────────

_hasher = _Argon2Hasher()


def hash_password(plain_password: str) -> str:
    """Return an Argon2id hash. Never raises on valid string input."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time-ish verify; returns False on any mismatch/malformed hash."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False
    except Exception:  # noqa: BLE001 — never let a bad hash crash login
        return False


def needs_rehash(password_hash: str) -> bool:
    """True if the hash was made with weaker/outdated Argon2 parameters."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except Exception:  # noqa: BLE001
        return False


# ─────────────────────────── JWT access tokens ───────────────────────────

TOKEN_USE_ACCESS = "access"


def create_access_token(
    *,
    sub: str,
    email: str,
    name: Optional[str] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> tuple[str, int]:
    """Mint a short-lived HS256 access token. Returns ``(token, expires_in)``."""
    now = datetime.now(timezone.utc)
    ttl = timedelta(minutes=settings.jwt_access_ttl_minutes)
    exp = now + ttl
    claims: dict[str, Any] = {
        "sub": sub,
        "email": email,
        "name": name or "",
        "token_use": TOKEN_USE_ACCESS,
        "iss": settings.jwt_issuer,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jose_jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")
    return token, int(ttl.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Verify signature + exp + issuer + token_use. Raises ``JWTError`` on failure."""
    claims = jose_jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"verify_aud": False, "leeway": settings.jwt_leeway_seconds},
    )
    if claims.get("token_use") != TOKEN_USE_ACCESS:
        raise JWTError(f"unexpected token_use={claims.get('token_use')!r}")
    return claims


# ─────────────────────────── refresh tokens (opaque) ───────────────────────────

def generate_refresh_token() -> str:
    """A high-entropy, URL-safe opaque token (not a JWT — tracked server-side)."""
    return secrets.token_urlsafe(48)


def generate_numeric_code(length: int = 6) -> str:
    """A short numeric code for email verification / password reset."""
    return "".join(secrets.choice("0123456789") for _ in range(length))
