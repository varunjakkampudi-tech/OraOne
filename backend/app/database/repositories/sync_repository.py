"""Sync job / log repositories (Phase 10)."""
from __future__ import annotations

import uuid

from sqlalchemy import select

from app.database.models.sync_job import SyncJob
from app.database.models.sync_log import SyncLog
from app.database.repositories.org_scoped import OrgScopedRepository


class SyncJobRepository(OrgScopedRepository[SyncJob]):
    model = SyncJob

    async def list_for_integration(
        self, integration_id: uuid.UUID, *, limit: int = 20
    ) -> list[SyncJob]:
        q = (
            select(SyncJob)
            .where(SyncJob.organization_id == self.organization_id)
            .where(SyncJob.integration_id == integration_id)
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(q)).all())


class SyncLogRepository(OrgScopedRepository[SyncLog]):
    model = SyncLog

    async def list_for_integration(
        self, integration_id: uuid.UUID, *, limit: int = 100
    ) -> list[SyncLog]:
        q = (
            select(SyncLog)
            .where(SyncLog.organization_id == self.organization_id)
            .where(SyncLog.integration_id == integration_id)
            .order_by(SyncLog.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(q)).all())
