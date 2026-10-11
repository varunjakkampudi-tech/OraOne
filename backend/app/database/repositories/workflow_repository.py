"""Workflow repository (Phase 11). Tenant-scoped helpers for workflows + runs."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.workflow import (
    RunStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStep,
    WorkflowStep,
    WorkflowVersion,
)


class WorkflowRepository:
    """All queries are pinned to ``organization_id``."""

    def __init__(
        self,
        session: AsyncSession,
        organization_id: uuid.UUID,
        project_id: Optional[uuid.UUID] = None,
    ) -> None:
        self.session = session
        self.organization_id = organization_id
        self.project_id = project_id

    # ── workflows ──
    async def get(self, workflow_id: uuid.UUID) -> Optional[Workflow]:
        row = await self.session.get(Workflow, workflow_id)
        if row is None or row.organization_id != self.organization_id or row.deleted_at is not None:
            return None
        return row

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Workflow]:
        q = (
            select(Workflow)
            .where(Workflow.organization_id == self.organization_id)
            .where(Workflow.deleted_at.is_(None))
            .order_by(Workflow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if self.project_id is not None:
            q = q.where(Workflow.project_id == self.project_id)
        return list((await self.session.scalars(q)).all())

    async def count(self) -> int:
        q = (
            select(func.count(Workflow.id))
            .where(Workflow.organization_id == self.organization_id)
            .where(Workflow.deleted_at.is_(None))
        )
        if self.project_id is not None:
            q = q.where(Workflow.project_id == self.project_id)
        return int((await self.session.scalar(q)) or 0)

    async def steps_for(self, workflow_id: uuid.UUID) -> list[WorkflowStep]:
        q = (
            select(WorkflowStep)
            .where(WorkflowStep.workflow_id == workflow_id)
            .where(WorkflowStep.organization_id == self.organization_id)
            .order_by(WorkflowStep.order_index)
        )
        return list((await self.session.scalars(q)).all())

    # ── runs ──
    async def get_run(self, run_id: uuid.UUID) -> Optional[WorkflowRun]:
        row = await self.session.get(WorkflowRun, run_id)
        if row is None or row.organization_id != self.organization_id:
            return None
        return row

    async def list_runs(
        self, *, workflow_id: Optional[uuid.UUID] = None, limit: int = 50, offset: int = 0
    ) -> list[WorkflowRun]:
        q = (
            select(WorkflowRun)
            .where(WorkflowRun.organization_id == self.organization_id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if workflow_id is not None:
            q = q.where(WorkflowRun.workflow_id == workflow_id)
        return list((await self.session.scalars(q)).all())

    async def count_runs(self, *, workflow_id: Optional[uuid.UUID] = None) -> int:
        q = (
            select(func.count(WorkflowRun.id))
            .where(WorkflowRun.organization_id == self.organization_id)
        )
        if workflow_id is not None:
            q = q.where(WorkflowRun.workflow_id == workflow_id)
        return int((await self.session.scalar(q)) or 0)

    async def run_steps_for(self, run_id: uuid.UUID) -> list[WorkflowRunStep]:
        q = (
            select(WorkflowRunStep)
            .where(WorkflowRunStep.run_id == run_id)
            .where(WorkflowRunStep.organization_id == self.organization_id)
            .order_by(WorkflowRunStep.order_index)
        )
        return list((await self.session.scalars(q)).all())

    # ── versions ──
    async def next_version_number(self, workflow_id: uuid.UUID) -> int:
        q = (
            select(func.coalesce(func.max(WorkflowVersion.version), 0))
            .where(WorkflowVersion.workflow_id == workflow_id)
            .where(WorkflowVersion.organization_id == self.organization_id)
        )
        return int((await self.session.scalar(q)) or 0) + 1

    async def list_versions(self, workflow_id: uuid.UUID) -> list[WorkflowVersion]:
        q = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .where(WorkflowVersion.organization_id == self.organization_id)
            .order_by(WorkflowVersion.version.desc())
        )
        return list((await self.session.scalars(q)).all())

    async def get_version(
        self, workflow_id: uuid.UUID, version: int
    ) -> Optional[WorkflowVersion]:
        q = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .where(WorkflowVersion.organization_id == self.organization_id)
            .where(WorkflowVersion.version == version)
        )
        return (await self.session.scalars(q)).first()

    # ── analytics ──
    async def analytics(self) -> dict:
        org = self.organization_id

        total_workflows = int(
            (
                await self.session.scalar(
                    select(func.count(Workflow.id))
                    .where(Workflow.organization_id == org)
                    .where(Workflow.deleted_at.is_(None))
                )
            )
            or 0
        )
        active_workflows = int(
            (
                await self.session.scalar(
                    select(func.count(Workflow.id))
                    .where(Workflow.organization_id == org)
                    .where(Workflow.deleted_at.is_(None))
                    .where(Workflow.status == "active")
                )
            )
            or 0
        )

        async def _count_runs(status: Optional[RunStatus]) -> int:
            q = select(func.count(WorkflowRun.id)).where(
                WorkflowRun.organization_id == org
            )
            if status is not None:
                q = q.where(WorkflowRun.status == status)
            return int((await self.session.scalar(q)) or 0)

        total_runs = await _count_runs(None)
        completed_runs = await _count_runs(RunStatus.completed)
        failed_runs = await _count_runs(RunStatus.failed)
        awaiting = await _count_runs(RunStatus.awaiting_approval)

        avg_seconds = await self.session.scalar(
            select(
                func.avg(
                    func.extract("epoch", WorkflowRun.finished_at)
                    - func.extract("epoch", WorkflowRun.started_at)
                )
            )
            .where(WorkflowRun.organization_id == org)
            .where(WorkflowRun.status == RunStatus.completed)
            .where(WorkflowRun.finished_at.isnot(None))
            .where(WorkflowRun.started_at.isnot(None))
        )

        most_used_rows = (
            await self.session.execute(
                select(
                    Workflow.id,
                    Workflow.name,
                    Workflow.run_count,
                    Workflow.success_count,
                )
                .where(Workflow.organization_id == org)
                .where(Workflow.deleted_at.is_(None))
                .order_by(Workflow.run_count.desc())
                .limit(5)
            )
        ).all()

        success_rate = (
            round((completed_runs / total_runs) * 100, 1) if total_runs else 0.0
        )

        return {
            "total_workflows": total_workflows,
            "active_workflows": active_workflows,
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "awaiting_approval": awaiting,
            "success_rate": success_rate,
            "avg_duration_seconds": round(float(avg_seconds), 2)
            if avg_seconds is not None
            else None,
            "most_used": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "run_count": r.run_count,
                    "success_count": r.success_count,
                }
                for r in most_used_rows
            ],
        }
