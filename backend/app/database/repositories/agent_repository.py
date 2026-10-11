"""Agent repository."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database.models.agent import Agent, AgentStatus
from app.database.repositories.base import BaseRepository
from app.database.repositories.org_scoped import OrgScopedRepository


class AgentRepository(BaseRepository[Agent]):
    model = Agent

    async def list_for_org(self, organization_id: uuid.UUID) -> list[Agent]:
        q = (
            select(Agent)
            .where(Agent.organization_id == organization_id)
            .where(Agent.deleted_at.is_(None))
            .order_by(Agent.created_at.desc())
        )
        return list((await self.session.scalars(q)).all())

    async def list_active_for_org(self, organization_id: uuid.UUID) -> list[Agent]:
        q = (
            select(Agent)
            .where(Agent.organization_id == organization_id)
            .where(Agent.status == AgentStatus.active)
            .where(Agent.deleted_at.is_(None))
        )
        return list((await self.session.scalars(q)).all())


class OrgScopedAgentRepository(OrgScopedRepository[Agent]):
    """Tenant-aware Agent repo — every query is pinned to the request's org."""

    model = Agent

    async def list_active(self) -> list[Agent]:
        q = (
            select(Agent)
            .where(Agent.organization_id == self.organization_id)
            .where(Agent.status == AgentStatus.active)
            .where(Agent.deleted_at.is_(None))
            .order_by(Agent.created_at.desc())
        )
        return list((await self.session.scalars(q)).all())
