"""User profile lookups — backed by Postgres (app.database.models.user.User).

Replaces the old DynamoDB-backed profile store; the Postgres ``users`` row
is now the single source of truth (no shadow copy to keep in sync).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.repositories.user_repository import UserRepository
from app.schemas.auth import UserProfile


async def get_user_profile(session: AsyncSession, user_id: str) -> Optional[UserProfile]:
    """``user_id`` is the JWT ``sub`` claim, stored as ``User.cognito_sub``."""
    users = UserRepository(session)
    user = await users.get_by_cognito_sub(user_id)
    if user is None:
        return None
    return UserProfile(
        userId=user.cognito_sub,
        email=user.email,
        name=user.full_name or "",
        role=user.role.value,
        plan="free",
        status=user.status.value,
        createdAt=user.created_at,
        lastLogin=user.last_login_at,
    )


async def update_profile(session: AsyncSession, user_id: str, *, full_name: str) -> Optional[UserProfile]:
    """Update the caller's display name. Returns the refreshed profile."""
    users = UserRepository(session)
    user = await users.get_by_cognito_sub(user_id)
    if user is None:
        return None
    user.full_name = full_name
    await session.commit()
    return await get_user_profile(session, user_id)
