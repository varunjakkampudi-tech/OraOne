"""User repository — keyed by auth subject for the post-login upsert path."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.database.models.user import User
from app.database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_auth_subject(self, auth_subject: str) -> Optional[User]:
        return await self.session.scalar(
            select(User).where(User.auth_subject == auth_subject)
        )

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.session.scalar(
            select(User).where(User.email == email.lower())
        )

    async def upsert_identity(
        self,
        *,
        auth_subject: str,
        email: str,
        full_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Find-or-create a user on first successful sign-in."""
        user = await self.get_by_auth_subject(auth_subject)
        by_email = await self.get_by_email(email)
        if (
            user is None
            and by_email is not None
            and by_email.auth_subject != auth_subject
        ):
            raise ValueError(
                "An account already exists for this verified email address."
            )
        if user is not None and by_email is not None and by_email.id != user.id:
            raise ValueError("The verified email address belongs to another account.")
        now = datetime.now(timezone.utc)
        if user is None:
            user = User(
                auth_subject=auth_subject,
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
