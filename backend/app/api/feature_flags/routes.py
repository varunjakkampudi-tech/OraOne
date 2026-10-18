"""Beta feature flag endpoints.

``GET /api/feature-flags`` returns the flags on for the caller. Any active
signed-in user can read it. Super-admins alone can change flags, and every
change is audited.
"""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.organization_member import MemberStatus, OrganizationMember
from app.database.session import get_db
from app.middleware.platform_context import (
    PlatformContext,
    get_current_platform_context,
    require_platform_role,
)
from app.services import feature_flags as flags
from app.services.audit import flush_pending

router = APIRouter(tags=["feature-flags"])
admin_router = APIRouter(
    prefix="/api/admin/feature-flags", tags=["admin-feature-flags"]
)


class OrganizationOverrideBody(BaseModel):
    # null removes the override, so the flag falls back to cohort and code rules.
    enabled: Optional[bool] = None


class CohortMemberBody(BaseModel):
    email: EmailStr
    # null removes the membership override.
    enabled: Optional[bool] = None


def _raise(exc: flags.FeatureFlagError) -> None:
    raise HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/feature-flags")
async def get_feature_flags(
    response: Response,
    organization_id: Optional[uuid.UUID] = None,
    ctx: PlatformContext = Depends(get_current_platform_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    org_scope: Optional[uuid.UUID] = None
    if organization_id is not None:
        # Only members can see org-level rollout for an organisation.
        membership = await db.scalar(
            select(OrganizationMember.id).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == ctx.user.id,
                OrganizationMember.status == MemberStatus.active,
                OrganizationMember.deleted_at.is_(None),
            )
        )
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this organization.",
            )
        org_scope = organization_id

    enabled = await flags.enabled_flag_keys(
        db, email=ctx.user.email, organization_id=org_scope
    )
    response.headers["Cache-Control"] = "private, max-age=60"
    return {"enabled": enabled, "cache_ttl_seconds": int(flags.CACHE_TTL_SECONDS)}


@admin_router.get("")
async def list_feature_flags(
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return {"flags": await flags.admin_overview(db)}


@admin_router.put("/{flag_key}/organizations/{organization_id}")
async def set_organization_override(
    flag_key: str,
    organization_id: uuid.UUID,
    payload: OrganizationOverrideBody,
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await flags.set_organization_override(
            db,
            flag_key=flag_key,
            organization_id=organization_id,
            enabled=payload.enabled,
            actor_id=ctx.user.id,
        )
    except flags.FeatureFlagError as exc:
        _raise(exc)
    await flush_pending(db)
    await db.commit()
    return result


@admin_router.put("/{flag_key}/cohort/members")
async def set_cohort_member(
    flag_key: str,
    payload: CohortMemberBody,
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        result = await flags.set_cohort_member(
            db,
            flag_key=flag_key,
            email=str(payload.email),
            enabled=payload.enabled,
            actor_id=ctx.user.id,
        )
    except flags.FeatureFlagError as exc:
        _raise(exc)
    await flush_pending(db)
    await db.commit()
    # The response never echoes the address.
    return result
