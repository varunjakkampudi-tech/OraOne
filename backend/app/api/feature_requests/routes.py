"""Feature requests / feedback board API.

In-product board where customers submit ideas, report bugs and give feedback,
then upvote what matters. Submitting and voting is open to any member; changing
the workflow status is reserved for owners/admins.

* ``GET    /api/feature-requests``              — list (filter by type/status/sort).
* ``POST   /api/feature-requests``              — submit an idea / bug / feedback.
* ``POST   /api/feature-requests/{id}/vote``    — toggle the caller's upvote.
* ``PATCH  /api/feature-requests/{id}/status``  — owner/admin status change.
* ``DELETE /api/feature-requests/{id}``         — author or admin removes a post.
* ``GET    /api/feature-requests/stats``        — board summary counts.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.feature_request import (
    FeatureRequest,
    FeatureRequestPriority,
    FeatureRequestStatus,
    FeatureRequestType,
)
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.schemas.feature_requests import (
    FeatureRequestCreate,
    FeatureRequestListResponse,
    FeatureRequestRead,
    FeatureRequestStats,
    FeatureRequestStatusUpdate,
)
from app.services.audit import audit


router = APIRouter(prefix="/api/feature-requests", tags=["feature-requests"])


def _to_read(row: FeatureRequest, user_id: uuid.UUID) -> FeatureRequestRead:
    voters = row.voter_ids or []
    return FeatureRequestRead(
        id=row.id,
        type=row.type,
        priority=row.priority,
        status=row.status,
        title=row.title,
        description=row.description,
        votes=row.votes,
        has_voted=str(user_id) in [str(v) for v in voters],
        is_author=row.user_id == user_id,
        author_name=row.author_name,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _validate_enum(value: str, allowed: tuple, label: str) -> str:
    v = (value or "").strip().lower()
    if v not in allowed:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid {label} {value!r}. Allowed: {', '.join(allowed)}.",
        )
    return v


@router.get("", response_model=FeatureRequestListResponse)
async def list_feature_requests(
    type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    sort: str = Query("top", pattern="^(top|new)$"),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FeatureRequestListResponse:
    stmt = select(FeatureRequest).where(
        FeatureRequest.organization_id == ctx.organization_id
    )
    if type:
        stmt = stmt.where(FeatureRequest.type == _validate_enum(type, FeatureRequestType.ALL, "type"))
    if status_filter:
        stmt = stmt.where(
            FeatureRequest.status == _validate_enum(status_filter, FeatureRequestStatus.ALL, "status")
        )
    if sort == "new":
        stmt = stmt.order_by(desc(FeatureRequest.created_at))
    else:
        stmt = stmt.order_by(desc(FeatureRequest.votes), desc(FeatureRequest.created_at))
    rows = (await session.scalars(stmt)).all()
    return FeatureRequestListResponse(
        items=[_to_read(r, ctx.user_id) for r in rows],
        total=len(rows),
    )


@router.get("/stats", response_model=FeatureRequestStats)
async def feature_request_stats(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FeatureRequestStats:
    rows = (
        await session.scalars(
            select(FeatureRequest).where(
                FeatureRequest.organization_id == ctx.organization_id
            )
        )
    ).all()
    by_status: dict[str, int] = {s: 0 for s in FeatureRequestStatus.ALL}
    by_type: dict[str, int] = {t: 0 for t in FeatureRequestType.ALL}
    for r in rows:
        by_status[r.status] = by_status.get(r.status, 0) + 1
        by_type[r.type] = by_type.get(r.type, 0) + 1
    return FeatureRequestStats(total=len(rows), by_status=by_status, by_type=by_type)


@router.post("", response_model=FeatureRequestRead, status_code=status.HTTP_201_CREATED)
async def create_feature_request(
    payload: FeatureRequestCreate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FeatureRequestRead:
    kind = _validate_enum(payload.type, FeatureRequestType.ALL, "type")
    prio = _validate_enum(payload.priority, FeatureRequestPriority.ALL, "priority")
    row = FeatureRequest(
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        author_name=(payload.author_name or "").strip() or None,
        type=kind,
        priority=prio,
        status=FeatureRequestStatus.OPEN,
        title=payload.title.strip(),
        description=(payload.description or "").strip() or None,
        votes=1,
        voter_ids=[str(ctx.user_id)],
    )
    session.add(row)
    await session.flush()
    await session.commit()
    await session.refresh(row)
    audit(
        "create",
        resource="feature_request",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"type": row.type, "title": row.title},
    )
    return _to_read(row, ctx.user_id)


async def _get_owned(
    session: AsyncSession, request_id: uuid.UUID, ctx: OrgContext
) -> FeatureRequest:
    row = await session.get(FeatureRequest, request_id)
    if row is None or row.organization_id != ctx.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Feature request not found.")
    return row


@router.post("/{request_id}/vote", response_model=FeatureRequestRead)
async def toggle_vote(
    request_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> FeatureRequestRead:
    row = await _get_owned(session, request_id, ctx)
    voters = [str(v) for v in (row.voter_ids or [])]
    uid = str(ctx.user_id)
    if uid in voters:
        voters.remove(uid)
    else:
        voters.append(uid)
    row.voter_ids = voters
    row.votes = len(voters)
    await session.commit()
    await session.refresh(row)
    return _to_read(row, ctx.user_id)


@router.patch("/{request_id}/status", response_model=FeatureRequestRead)
async def update_status(
    request_id: uuid.UUID,
    payload: FeatureRequestStatusUpdate,
    ctx: OrgContext = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_db),
) -> FeatureRequestRead:
    row = await _get_owned(session, request_id, ctx)
    row.status = _validate_enum(payload.status, FeatureRequestStatus.ALL, "status")
    await session.commit()
    await session.refresh(row)
    audit(
        "update",
        resource="feature_request",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"status": row.status},
    )
    return _to_read(row, ctx.user_id)


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_feature_request(
    request_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> Response:
    row = await _get_owned(session, request_id, ctx)
    role = (getattr(ctx, "membership_role", "") or "").lower()
    if row.user_id != ctx.user_id and role not in ("owner", "admin"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the author or an admin can remove this post.",
        )
    await session.delete(row)
    await session.commit()
    audit(
        "delete",
        resource="feature_request",
        resource_id=str(request_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
