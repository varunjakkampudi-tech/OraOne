"""Platform-admin (Super Admin Control Center) authentication.

The customer dashboard is org-scoped via :func:`get_current_organization`.
The Super Admin Control Center is *platform*-scoped: a tiny allow-list of
founder / platform-administrator emails who may read and operate across every
tenant.

Trust model (defence in depth):
  1. The caller must present a valid access token (verified upstream by
     :func:`get_current_user_claims`).
  2. Their email — resolved from the *server-side* ``users`` row, never the
     token body — must appear in ``PLATFORM_ADMIN_EMAILS``.

Anything else is a hard 403. The allow-list is intentionally an environment
variable (not a DB row) so it cannot be edited from inside the running app.

Unlike :func:`get_current_organization`, this dependency does **not** stamp the
session with ``app.org_id`` — platform admins read across tenants, so no RLS
tenant pin is applied.
"""
from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_user_claims

log = logging.getLogger("app.super_admin")


@lru_cache(maxsize=1)
def _admin_allowlist() -> frozenset[str]:
    """Parse ``PLATFORM_ADMIN_EMAILS`` into a normalised email set."""
    raw = os.environ.get("PLATFORM_ADMIN_EMAILS", "")
    emails = {e.strip().lower() for e in raw.split(",") if e.strip()}
    if not emails:
        log.warning(
            "PLATFORM_ADMIN_EMAILS is empty — the Super Admin Control Center "
            "is locked to everyone until it is configured."
        )
    return frozenset(emails)


def is_platform_admin_email(email: str | None) -> bool:
    return bool(email) and email.strip().lower() in _admin_allowlist()


@dataclass(frozen=True)
class PlatformAdminContext:
    """Verified identity of a platform administrator."""

    user_id: uuid.UUID
    cognito_sub: str
    email: str
    full_name: str | None


async def get_platform_admin(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
) -> PlatformAdminContext:
    """FastAPI dependency: resolve + authorise the calling platform admin."""
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims.",
        )

    user = await session.scalar(
        select(User).where(User.cognito_sub == cognito_sub)
    )
    if user is None or not is_platform_admin_email(user.email):
        # Same opaque message whether the user is unknown or simply not an
        # admin — never reveal the allow-list contents.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )

    return PlatformAdminContext(
        user_id=user.id,
        cognito_sub=cognito_sub,
        email=user.email,
        full_name=user.full_name,
    )
