"""Team repository — members + invitations (Phase 12, Module 3).

All queries are scoped to a single ``organization_id`` to preserve tenant
isolation.
"""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.organization_invitation import (
    InvitationStatus,
    OrganizationInvitation,
)
from app.database.models.organization_member import (
    MemberStatus,
    OrganizationMember,
)
from app.database.models.user import User


class TeamRepository:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    # ---- members ----
    async def list_members(self) -> Sequence[tuple[OrganizationMember, User]]:
        rows = await self.session.execute(
            select(OrganizationMember, User)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == self.organization_id)
            .where(OrganizationMember.deleted_at.is_(None))
            .where(OrganizationMember.status != MemberStatus.removed)
            .order_by(OrganizationMember.joined_at.asc().nullsfirst())
        )
        return [(m, u) for m, u in rows.all()]

    async def get_member(self, member_id: uuid.UUID) -> Optional[OrganizationMember]:
        return await self.session.scalar(
            select(OrganizationMember)
            .where(OrganizationMember.id == member_id)
            .where(OrganizationMember.organization_id == self.organization_id)
            .where(OrganizationMember.deleted_at.is_(None))
        )

    async def find_member_by_email(self, email: str) -> Optional[OrganizationMember]:
        return await self.session.scalar(
            select(OrganizationMember)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == self.organization_id)
            .where(OrganizationMember.deleted_at.is_(None))
            .where(func.lower(User.email) == email.lower())
        )

    async def count_owners(self) -> int:
        from app.database.models.organization_member import MemberRole

        return int(
            await self.session.scalar(
                select(func.count(OrganizationMember.id))
                .where(OrganizationMember.organization_id == self.organization_id)
                .where(OrganizationMember.deleted_at.is_(None))
                .where(OrganizationMember.role == MemberRole.owner)
                .where(OrganizationMember.status != MemberStatus.removed)
            )
            or 0
        )

    # ---- invitations ----
    async def list_invitations(
        self, *, only_pending: bool = False
    ) -> Sequence[OrganizationInvitation]:
        q = (
            select(OrganizationInvitation)
            .options(selectinload(OrganizationInvitation.invited_by))
            .where(OrganizationInvitation.organization_id == self.organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
        if only_pending:
            q = q.where(OrganizationInvitation.status == InvitationStatus.pending)
        return (await self.session.scalars(q)).all()

    async def get_invitation(
        self, invitation_id: uuid.UUID
    ) -> Optional[OrganizationInvitation]:
        return await self.session.scalar(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.id == invitation_id)
            .where(OrganizationInvitation.organization_id == self.organization_id)
        )

    async def find_pending_invitation_by_email(
        self, email: str
    ) -> Optional[OrganizationInvitation]:
        return await self.session.scalar(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == self.organization_id)
            .where(func.lower(OrganizationInvitation.email) == email.lower())
            .where(OrganizationInvitation.status == InvitationStatus.pending)
        )

    @staticmethod
    async def get_invitation_by_token(
        session: AsyncSession, token: str
    ) -> Optional[OrganizationInvitation]:
        """Token lookup is intentionally NOT org-scoped (the accepting user
        may not yet belong to the org)."""
        return await session.scalar(
            select(OrganizationInvitation).where(
                OrganizationInvitation.token == token
            )
        )
