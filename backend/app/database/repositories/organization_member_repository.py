"""OrganizationMember repository."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.database.models.organization_member import (
    MemberRole,
    MemberStatus,
    OrganizationMember,
)
from app.database.repositories.base import BaseRepository


class OrganizationMemberRepository(BaseRepository[OrganizationMember]):
    model = OrganizationMember

    async def find(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Optional[OrganizationMember]:
        return await self.session.scalar(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )

    async def ensure_membership(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MemberRole = MemberRole.member,
        invited_by_user_id: Optional[uuid.UUID] = None,
    ) -> OrganizationMember:
        existing = await self.find(
            organization_id=organization_id, user_id=user_id
        )
        if existing is not None:
            return existing
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            status=MemberStatus.active,
            invited_by_user_id=invited_by_user_id,
            joined_at=datetime.now(timezone.utc),
        )
        self.session.add(member)
        await self.session.flush()
        return member
