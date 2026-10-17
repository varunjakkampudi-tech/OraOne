"""Do-not-contact list API: who this organization must never call or message.

Entries apply to the whole organization, across projects, so the routes scope
by organization only. Reads need ``leads.read``; changes need ``leads.write``.
Phone numbers are never written to logs or audit metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.do_not_contact import DoNotContact
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.services import contact_policy_service as svc
from app.services.audit import audit
from app.services.authorization import require_permission

router = APIRouter(prefix="/api/contact-policy", tags=["contact-policy"])


class DoNotContactRead(BaseModel):
    id: uuid.UUID
    value: str
    channel_scope: str
    reason: str
    source: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime


class DoNotContactCreate(BaseModel):
    value: str = Field(
        min_length=1, max_length=255, description="Phone (E.164) or email"
    )
    channel_scope: Literal["all", "call", "sms", "whatsapp", "email", "instagram"] = (
        "all"
    )
    reason: str = Field(default="", max_length=svc.MAX_REASON_LENGTH)


def _to_read(entry: DoNotContact) -> DoNotContactRead:
    return DoNotContactRead(
        id=entry.id,
        value=entry.normalised_value,
        channel_scope=entry.channel_scope,
        reason=entry.reason or "",
        source=entry.source,
        created_by=entry.created_by,
        created_at=entry.created_at,
    )


@router.get("/do-not-contact", response_model=list[DoNotContactRead])
async def list_do_not_contact(
    ctx: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[DoNotContactRead]:
    entries = await svc.list_entries(session, organization_id=ctx.organization_id)
    return [_to_read(e) for e in entries]


@router.post(
    "/do-not-contact",
    response_model=DoNotContactRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_do_not_contact(
    payload: DoNotContactCreate,
    response: Response,
    ctx: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    session: AsyncSession = Depends(get_db),
) -> DoNotContactRead:
    try:
        entry, created = await svc.add_entry(
            session,
            organization_id=ctx.organization_id,
            raw_value=payload.value,
            channel_scope=payload.channel_scope,
            reason=payload.reason,
            created_by=ctx.user_id,
        )
    except svc.ContactEntryError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    if created:
        audit(
            "create",
            resource="do_not_contact",
            organization_id=str(ctx.organization_id),
            user_id=str(ctx.user_id),
            resource_id=str(entry.id),
            meta={"channel_scope": entry.channel_scope, "source": entry.source},
        )
    else:
        response.status_code = status.HTTP_200_OK
    await session.commit()
    await session.refresh(entry)
    return _to_read(entry)


@router.delete("/do-not-contact/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_do_not_contact(
    entry_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    session: AsyncSession = Depends(get_db),
) -> Response:
    removed = await svc.remove_entry(
        session, organization_id=ctx.organization_id, entry_id=entry_id
    )
    if not removed:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That entry was not found.")
    audit(
        "delete",
        resource="do_not_contact",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        resource_id=str(entry_id),
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
