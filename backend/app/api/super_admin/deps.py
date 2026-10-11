"""Platform-admin (Super Admin Control Center) authentication.

The customer dashboard is org-scoped via :func:`get_current_organization`.
The Super Admin Control Center is *platform*-scoped and is authorized from
the PostgreSQL ``users.role`` value after resolving the verified Cognito sub.

Trust model (defence in depth):
  1. The caller must present a valid access token (verified upstream by
     :func:`get_current_user_claims`).
  2. Their server-side PostgreSQL platform role must be ``super_admin`` or
     ``admin``. Organization membership roles and token role claims are not
     sufficient.

Anything else is a hard 403.

Unlike :func:`get_current_organization`, this dependency does **not** stamp the
session with ``app.org_id`` — platform admins read across tenants, so no RLS
tenant pin is applied.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_user_claims

log = logging.getLogger("app.super_admin")


@dataclass(frozen=True)
class PlatformAdminContext:
    """Verified identity of a platform administrator."""

    user_id: uuid.UUID
    cognito_sub: str
    email: str
    full_name: str | None
    role: UserRole


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

    user = await session.scalar(select(User).where(User.cognito_sub == cognito_sub))
    if user is None or user.role not in {UserRole.super_admin, UserRole.admin}:
        # Same opaque message whether the user is unknown or simply not an
        # administrator — never reveal role policy details.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required.",
        )

    return PlatformAdminContext(
        user_id=user.id,
        cognito_sub=cognito_sub,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
    )
