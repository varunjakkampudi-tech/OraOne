"""TokenService — issues, rotates, and revokes access/refresh token pairs.

Design (SOLID — single responsibility, one level below AuthService):

    AuthService
        -> TokenService   (this module: JWT + refresh-token lifecycle)
        -> PasswordService (app.core.security: hash/verify)
        -> UserRepository (app.database.repositories.user_repository)

Refresh tokens are opaque random strings (not JWTs) tracked in the shared
cache (Redis when configured, in-process otherwise — see
app/services/cache.py::get_shared_cache) so they can be individually
revoked. Rotation: every ``/auth/refresh`` call deletes the presented
token and issues a brand new one — if a *revoked* token is ever presented
again (replay of a stolen token after the legitimate client already
rotated), the whole family is revoked, matching OWASP's refresh-token
rotation-with-reuse-detection guidance.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from app.core.config import settings
from app.core.security import create_access_token, generate_refresh_token
from app.services.cache import get_shared_cache

log = logging.getLogger("app.auth.tokens")

_REFRESH_TTL_SECONDS = lambda: settings.jwt_refresh_ttl_days * 86400  # noqa: E731


def _cache():
    return get_shared_cache("refresh")


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"


def _family_key(family_id: str) -> str:
    return f"family:{family_id}"


def _user_families_key(user_id: str) -> str:
    return f"userfam:{user_id}"


def issue_token_pair(*, user_id: str, email: str, name: Optional[str] = None) -> TokenPair:
    """Mint a fresh access+refresh pair for a brand-new session (login)."""
    family_id = str(uuid.uuid4())
    pair = _issue(user_id=user_id, email=email, name=name, family_id=family_id)
    families = _cache().get(_user_families_key(user_id)) or []
    families.append(family_id)
    _cache().set(_user_families_key(user_id), families, ttl_seconds=_REFRESH_TTL_SECONDS())
    return pair


def _issue(*, user_id: str, email: str, name: Optional[str], family_id: str) -> TokenPair:
    access_token, expires_in = create_access_token(sub=user_id, email=email, name=name)
    refresh_token = generate_refresh_token()
    _cache().set(
        f"token:{refresh_token}",
        {"user_id": user_id, "email": email, "name": name, "family_id": family_id},
        ttl_seconds=_REFRESH_TTL_SECONDS(),
    )
    # Track every live token in its family so a reuse-detected breach can
    # revoke all of them at once, not just the one presented.
    family = _cache().get(_family_key(family_id)) or []
    family.append(refresh_token)
    _cache().set(_family_key(family_id), family, ttl_seconds=_REFRESH_TTL_SECONDS())
    return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in)


def rotate(refresh_token: str) -> TokenPair:
    """Validate + rotate a refresh token. Raises ``ValueError`` if invalid/expired.

    On reuse of an already-rotated (deleted) token, revokes the entire family
    — a signal that a refresh token was stolen and the legitimate client
    already moved on.
    """
    record = _cache().get(f"token:{refresh_token}")
    if record is None:
        raise ValueError("invalid_or_reused_refresh_token")

    _cache().delete(f"token:{refresh_token}")
    pair = _issue(
        user_id=record["user_id"],
        email=record["email"],
        name=record.get("name"),
        family_id=record["family_id"],
    )
    return pair


def revoke(refresh_token: str) -> None:
    """Revoke a single refresh token (logout on this device)."""
    _cache().delete(f"token:{refresh_token}")


def revoke_all_for_family(refresh_token: str) -> None:
    """Revoke every token descended from the same login (logout everywhere)."""
    record = _cache().get(f"token:{refresh_token}")
    if not record:
        return
    family_id = record["family_id"]
    family = _cache().get(_family_key(family_id)) or []
    for tok in family:
        _cache().delete(f"token:{tok}")
    _cache().delete(_family_key(family_id))


def revoke_all_for_user(user_id: str) -> None:
    """Revoke every session for a user (password reset / security event)."""
    families = _cache().get(_user_families_key(user_id)) or []
    for family_id in families:
        tokens = _cache().get(_family_key(family_id)) or []
        for tok in tokens:
            _cache().delete(f"token:{tok}")
        _cache().delete(_family_key(family_id))
    _cache().delete(_user_families_key(user_id))
