"""User repository — keyed by Cognito sub for the post-login upsert path."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.database.models.user import User
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_cognito_sub(self, cognito_sub: str) -> Optional[User]:
        return await self.session.scalar(
            select(User).where(User.cognito_sub == cognito_sub)
        )

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.session.scalar(
            select(User).where(User.email == email.lower())
        )

    async def upsert_from_cognito(
        self,
        *,
        cognito_sub: str,
        email: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Find-or-create a user on first successful Cognito login."""
        user = await self.get_by_cognito_sub(cognito_sub)
        now = datetime.now(timezone.utc)
        if user is None:
            user = User(
                cognito_sub=cognito_sub,
                email=email.lower(),
                full_name=full_name,
                avatar_url=avatar_url,
                last_login_at=now,
            )
            self.session.add(user)
        else:
            # Lightweight refresh of mutable fields
            user.email = email.lower()
            if full_name and not user.full_name:
                user.full_name = full_name
            if avatar_url:
                user.avatar_url = avatar_url
            user.last_login_at = now
        await self.session.flush()
        return user
