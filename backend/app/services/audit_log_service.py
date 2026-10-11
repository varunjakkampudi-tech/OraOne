"""Audit log query service (Phase 12, Module 5)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.audit_log import AuditLog

MAX_LIMIT = 200


async def list_logs(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    user_id: Optional[uuid.UUID] = None,
    days: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AuditLog], int]:
    """Return a page of audit logs (newest first) plus the total count."""
    limit = max(1, min(int(limit or 50), MAX_LIMIT))
    offset = max(0, int(offset or 0))

    conds = [AuditLog.organization_id == organization_id]
    if action:
        conds.append(AuditLog.action == action)
    if resource:
        conds.append(AuditLog.resource == resource)
    if user_id is not None:
        conds.append(AuditLog.user_id == user_id)
    if days and days > 0:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        conds.append(AuditLog.created_at >= since)

    total = await session.scalar(
        select(func.count()).select_from(AuditLog).where(*conds)
    )
    rows = (
        await session.scalars(
            select(AuditLog)
            .where(*conds)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows), int(total or 0)


async def facets(session: AsyncSession, organization_id: uuid.UUID) -> dict:
    """Distinct actions and resources present for this org (for filters)."""
    actions = (
        await session.scalars(
            select(AuditLog.action)
            .where(AuditLog.organization_id == organization_id)
            .distinct()
            .order_by(AuditLog.action)
        )
    ).all()
    resources = (
        await session.scalars(
            select(AuditLog.resource)
            .where(AuditLog.organization_id == organization_id)
            .distinct()
            .order_by(AuditLog.resource)
        )
    ).all()
    return {"actions": list(actions), "resources": list(resources)}
