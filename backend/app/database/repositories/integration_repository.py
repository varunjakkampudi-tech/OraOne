"""Integration repository."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select

from app.database.models.integration import Integration
from app.database.repositories.base import BaseRepository
from app.database.repositories.org_scoped import OrgScopedRepository


class IntegrationRepository(BaseRepository[Integration]):
    model = Integration

    async def list_for_org(self, organization_id: uuid.UUID) -> list[Integration]:
        q = (
            select(Integration)
            .where(Integration.organization_id == organization_id)
            .where(Integration.deleted_at.is_(None))
        )
        return list((await self.session.scalars(q)).all())

    async def get_by_provider(
        self, organization_id: uuid.UUID, provider: str
    ) -> Optional[Integration]:
        return await self.session.scalar(
            select(Integration).where(
                Integration.organization_id == organization_id,
                Integration.provider == provider,
            )
        )


class OrgScopedIntegrationRepository(OrgScopedRepository[Integration]):
    """Tenant-aware Integration repo."""

    model = Integration

    async def get_by_provider(self, provider: str) -> Optional[Integration]:
        return await self.session.scalar(
            select(Integration)
            .where(Integration.organization_id == self.organization_id)
            .where(Integration.provider == provider)
            .where(Integration.deleted_at.is_(None))
        )
