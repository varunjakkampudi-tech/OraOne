"""Escalation queue for the active project.

Every query is scoped to the caller's organization and active project. Access
uses the leads permissions, because escalations are lead follow-ups.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.escalation import Escalation, EscalationStatus
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import escalation_service
from app.services.authorization import require_permission

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


class EscalationRead(BaseModel):
    id: uuid.UUID
    channel: str
    question: str
    status: str
    has_contact: bool
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    assigned_user_id: Optional[uuid.UUID] = None
    notify_status: str
    notify_attempts: int
    last_error: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class AssignRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None


def _to_read(row: Escalation) -> EscalationRead:
    return EscalationRead(
        id=row.id,
        channel=row.channel,
        question=row.question,
        status=row.status,
        has_contact=row.has_contact,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        contact_phone=row.contact_phone,
        assigned_user_id=row.assigned_user_id,
        notify_status=row.notify_status,
        notify_attempts=row.notify_attempts,
        last_error=row.last_error,
        created_at=row.created_at,
        resolved_at=row.resolved_at,
    )


async def _load(
    session: AsyncSession, pctx: ProjectContext, escalation_id: uuid.UUID
) -> Escalation:
    row = await session.scalar(
        select(Escalation)
        .where(Escalation.id == escalation_id)
        .where(Escalation.organization_id == pctx.organization_id)
        .where(Escalation.project_id == pctx.project_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return row


@router.get("", response_model=list[EscalationRead])
async def list_escalations(
    status_: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[EscalationRead]:
    query = (
        select(Escalation)
        .where(Escalation.organization_id == pctx.organization_id)
        .where(Escalation.project_id == pctx.project_id)
    )
    if status_:
        if status_ not in EscalationStatus.ALL:
            raise HTTPException(status_code=422, detail="Unknown status.")
        query = query.where(Escalation.status == status_)
    rows = await session.execute(
        query.order_by(Escalation.created_at.desc()).limit(limit).offset(offset)
    )
    return [_to_read(r) for r in rows.scalars().all()]


@router.post("/{escalation_id}/assign", response_model=EscalationRead)
async def assign_escalation(
    escalation_id: uuid.UUID,
    payload: AssignRequest,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationRead:
    row = await _load(session, pctx, escalation_id)
    if payload.user_id is not None:
        member = await session.scalar(
            select(OrganizationMember.id)
            .where(OrganizationMember.organization_id == pctx.organization_id)
            .where(OrganizationMember.user_id == payload.user_id)
            .where(OrganizationMember.status == MemberStatus.active)
            .where(OrganizationMember.deleted_at.is_(None))
        )
        if member is None:
            raise HTTPException(
                status_code=422,
                detail="Assignee is not an active member of this organization.",
            )
    await escalation_service.assign(session, row, user_id=payload.user_id)
    await session.commit()
    return _to_read(row)


@router.post("/{escalation_id}/resolve", response_model=EscalationRead)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationRead:
    row = await _load(session, pctx, escalation_id)
    await escalation_service.resolve(session, row)
    await session.commit()
    return _to_read(row)
