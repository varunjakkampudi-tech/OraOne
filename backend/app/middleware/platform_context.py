"""Server-side platform-role resolution.

Organization membership roles are deliberately separate from platform roles.
This dependency resolves the authenticated token subject to PostgreSQL and
never trusts a role supplied by a browser or copied from an unvalidated token.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.user import User, UserRole
from app.database.session import get_db
from app.middleware.jwt_auth import get_current_user_claims


@dataclass(frozen=True)
class PlatformContext:
    user: User
    auth_subject: str
    role: UserRole


async def get_current_platform_context(
    claims: dict = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db),
) -> PlatformContext:
    auth_subject = claims.get("sub")
    if not auth_subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims."
        )
    user = await session.scalar(select(User).where(User.auth_subject == auth_subject))
    if user is None or user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform identity is not active.",
        )
    return PlatformContext(user=user, auth_subject=auth_subject, role=user.role)


def require_platform_role(*allowed: str):
    allowed_set = {value.lower() for value in allowed}

    async def _checker(
        ctx: PlatformContext = Depends(get_current_platform_context),
    ) -> PlatformContext:
        if ctx.role.value not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform role is not permitted for this operation.",
            )
        return ctx

    return _checker
