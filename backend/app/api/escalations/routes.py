"""Escalation inbox for the active project.

Every query is scoped to the caller's organization and active project. Reads use
the leads read permission; changes use the leads write permission, because
escalations are lead follow-ups.

Internal notes are returned to the team only. They never reach a visitor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.escalation import (
    Escalation,
    EscalationStatus,
    NotifyStatus,
)
from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import escalation_service
from app.services.authorization import require_permission

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


class NoteRead(BaseModel):
    at: str
    user_id: str
    text: str


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
    due_at: Optional[datetime] = None
    overdue: bool
    internal_notes: list[NoteRead] = Field(default_factory=list)
    created_at: datetime
    resolved_at: Optional[datetime] = None
    first_reply_at: Optional[datetime] = None


class EscalationSummary(BaseModel):
    open: int
    assigned: int
    resolved: int
    overdue: int
    notify_failed: int
    dead_letter: int
    no_recipients: int


class AssignRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None


class NoteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


def _to_read(row: Escalation, now: Optional[datetime] = None) -> EscalationRead:
    notes: list[Any] = list(row.internal_notes or [])
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
        due_at=row.due_at,
        overdue=escalation_service.is_overdue(row, now or datetime.now(timezone.utc)),
        internal_notes=[NoteRead(**note) for note in notes if isinstance(note, dict)],
        created_at=row.created_at,
        resolved_at=row.resolved_at,
        first_reply_at=row.first_reply_at,
    )


def _project_scope(query, pctx: ProjectContext):
    return query.where(Escalation.organization_id == pctx.organization_id).where(
        Escalation.project_id == pctx.project_id
    )


async def _load(
    session: AsyncSession, pctx: ProjectContext, escalation_id: uuid.UUID
) -> Escalation:
    row = await session.scalar(
        _project_scope(select(Escalation).where(Escalation.id == escalation_id), pctx)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    return row


async def _check_member(
    session: AsyncSession, pctx: ProjectContext, user_id: uuid.UUID
) -> None:
    member = await session.scalar(
        select(OrganizationMember.id)
        .where(OrganizationMember.organization_id == pctx.organization_id)
        .where(OrganizationMember.user_id == user_id)
        .where(OrganizationMember.status == MemberStatus.active)
        .where(OrganizationMember.deleted_at.is_(None))
    )
    if member is None:
        raise HTTPException(
            status_code=422,
            detail="Assignee is not an active member of this organization.",
        )


@router.get("/summary", response_model=EscalationSummary)
async def escalation_summary(
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationSummary:
    now = datetime.now(timezone.utc)
    rows = await session.execute(
        _project_scope(
            select(
                Escalation.status,
                Escalation.notify_status,
                func.count(Escalation.id),
                func.count(Escalation.id).filter(
                    Escalation.status != EscalationStatus.resolved,
                    Escalation.due_at.is_not(None),
                    Escalation.due_at < now,
                ),
            ).group_by(Escalation.status, Escalation.notify_status),
            pctx,
        )
    )
    counts = {
        "open": 0,
        "assigned": 0,
        "resolved": 0,
        "overdue": 0,
        "notify_failed": 0,
        "dead_letter": 0,
        "no_recipients": 0,
    }
    for status_value, notify_value, total, overdue_total in rows.all():
        counts[status_value] = counts.get(status_value, 0) + total
        counts["overdue"] += overdue_total
        if notify_value == NotifyStatus.failed:
            counts["notify_failed"] += total
        if notify_value == NotifyStatus.dead_letter:
            counts["dead_letter"] += total
        if notify_value == NotifyStatus.no_recipients:
            counts["no_recipients"] += total
    return EscalationSummary(**counts)


@router.get("", response_model=list[EscalationRead])
async def list_escalations(
    status_: Optional[str] = Query(default=None, alias="status"),
    overdue: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[EscalationRead]:
    query = _project_scope(select(Escalation), pctx)
    if status_:
        if status_ not in EscalationStatus.ALL:
            raise HTTPException(status_code=422, detail="Unknown status.")
        query = query.where(Escalation.status == status_)
    if overdue:
        now = datetime.now(timezone.utc)
        query = query.where(
            Escalation.status != EscalationStatus.resolved,
            Escalation.due_at.is_not(None),
            Escalation.due_at < now,
        )
    rows = await session.execute(
        query.order_by(Escalation.created_at.desc()).limit(limit).offset(offset)
    )
    now = datetime.now(timezone.utc)
    return [_to_read(r, now) for r in rows.scalars().all()]


@router.get("/{escalation_id}", response_model=EscalationRead)
async def get_escalation(
    escalation_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationRead:
    return _to_read(await _load(session, pctx, escalation_id))


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
        await _check_member(session, pctx, payload.user_id)
    await escalation_service.assign(session, row, user_id=payload.user_id)
    await session.commit()
    return _to_read(row)


@router.post("/{escalation_id}/notes", response_model=EscalationRead)
async def add_escalation_note(
    escalation_id: uuid.UUID,
    payload: NoteRequest,
    ctx: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationRead:
    row = await _load(session, pctx, escalation_id)
    await escalation_service.add_note(
        session, row, user_id=ctx.user_id, text=payload.text
    )
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


@router.post("/{escalation_id}/reopen", response_model=EscalationRead)
async def reopen_escalation(
    escalation_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> EscalationRead:
    row = await _load(session, pctx, escalation_id)
    await escalation_service.reopen(session, row)
    await session.commit()
    return _to_read(row)
