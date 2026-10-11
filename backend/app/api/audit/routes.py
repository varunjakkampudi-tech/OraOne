"""Phase 12 Module 5 — Audit log viewer API.

* ``GET /api/audit-logs`` — paginated, filterable org-scoped audit trail
  with action/resource facets and resolved actor identities.

Requires ``settings.read`` (owners/admins). Audit records themselves are
written by ``app.services.audit`` and flushed by middleware.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.org_context import OrgContext, require_permission
from app.schemas.audit_logs import (
    AuditLogActor,
    AuditLogListResponse,
    AuditLogOut,
)
from app.services import audit_log_service
from app.services.audit import flush_pending

router = APIRouter(tags=["audit"])


@router.get("/api/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = Query(None),
    resource: Optional[str] = Query(None),
    user_id: Optional[uuid.UUID] = Query(None),
    days: Optional[int] = Query(None, ge=1, le=365),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> AuditLogListResponse:
    # Persist anything still buffered so the view is fully up to date.
    await flush_pending(session)

    logs, total = await audit_log_service.list_logs(
        session,
        ctx.organization_id,
        action=action,
        resource=resource,
        user_id=user_id,
        days=days,
        limit=limit,
        offset=offset,
    )
    facet = await audit_log_service.facets(session, ctx.organization_id)

    actor_ids = {l.user_id for l in logs if l.user_id is not None}
    actors: dict[str, AuditLogActor] = {}
    if actor_ids:
        users = (
            await session.scalars(select(User).where(User.id.in_(actor_ids)))
        ).all()
        for u in users:
            actors[str(u.id)] = AuditLogActor(
                id=u.id, name=u.full_name, email=u.email
            )

    return AuditLogListResponse(
        logs=[AuditLogOut.model_validate(l) for l in logs],
        total=total,
        limit=limit,
        offset=offset,
        actions=facet["actions"],
        resources=facet["resources"],
        actors=actors,
    )
