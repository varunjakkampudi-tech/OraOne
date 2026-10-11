"""Conversation repository."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select

from app.database.models.conversation import Conversation, ConversationStatus
from app.database.repositories.base import BaseRepository
from app.database.repositories.org_scoped import OrgScopedRepository


class ConversationRepository(BaseRepository[Conversation]):
    model = Conversation

    async def list_for_org(
        self,
        organization_id: uuid.UUID,
        *,
        status: Optional[ConversationStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        q = (
            select(Conversation)
            .where(Conversation.organization_id == organization_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(Conversation.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            q = q.where(Conversation.status == status)
        return list((await self.session.scalars(q)).all())

    async def list_for_agent(
        self, agent_id: uuid.UUID, *, limit: int = 50
    ) -> list[Conversation]:
        q = (
            select(Conversation)
            .where(Conversation.agent_id == agent_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(Conversation.started_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(q)).all())


class OrgScopedConversationRepository(OrgScopedRepository[Conversation]):
    """Tenant-aware Conversation repo — pinned to the request's org."""

    model = Conversation

    async def list_filtered(
        self,
        *,
        status: Optional[ConversationStatus] = None,
        agent_id: Optional[uuid.UUID] = None,
        project_id: Optional[uuid.UUID] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Conversation]:
        q = (
            select(Conversation)
            .where(Conversation.organization_id == self.organization_id)
            .where(Conversation.deleted_at.is_(None))
            .order_by(Conversation.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if status is not None:
            q = q.where(Conversation.status == status)
        if agent_id is not None:
            q = q.where(Conversation.agent_id == agent_id)
        if project_id is not None:
            q = q.where(Conversation.project_id == project_id)
        return list((await self.session.scalars(q)).all())
