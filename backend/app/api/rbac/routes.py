"""Phase 12 Module 4 — RBAC API.

Lightweight, read-only endpoints that expose the permission matrix so the
frontend can gate UI and so integrators can introspect their role's
capabilities. Authorisation enforcement happens at each guarded endpoint
via ``require_permission`` — these routes only *describe* access.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import (
    ALL_PERMISSIONS,
    permissions_for,
    role_matrix,
)
from app.middleware.org_context import OrgContext, get_current_organization
from app.database.session import get_db
from app.middleware.platform_context import PlatformContext, require_platform_role
from app.schemas.rbac import (
    MyPermissionsResponse,
    PlatformRoleUpdateRequest,
    PlatformUserRoleResponse,
    RoleMatrixResponse,
)
from app.services.platform_rbac import change_platform_role

router = APIRouter(tags=["rbac"])


@router.get("/api/rbac/me", response_model=MyPermissionsResponse)
async def my_permissions(
    ctx: OrgContext = Depends(get_current_organization),
) -> MyPermissionsResponse:
    """Return the caller's role and the permissions it grants."""
    return MyPermissionsResponse(
        role=ctx.membership_role,
        platform_role=ctx.platform_role,
        permissions=sorted(permissions_for(ctx.membership_role)),
    )


@router.get("/api/rbac/matrix", response_model=RoleMatrixResponse)
async def permission_matrix(
    _ctx: OrgContext = Depends(get_current_organization),
) -> RoleMatrixResponse:
    """Return the full role → permissions matrix and the permission list."""
    return RoleMatrixResponse(
        permissions=list(ALL_PERMISSIONS),
        roles=role_matrix(),
    )


@router.patch("/api/rbac/platform/users/{user_id}/role", response_model=PlatformUserRoleResponse)
async def change_user_platform_role(
    user_id: uuid.UUID,
    payload: PlatformRoleUpdateRequest,
    ctx: PlatformContext = Depends(require_platform_role("super_admin", "admin")),
    session: AsyncSession = Depends(get_db),
) -> PlatformUserRoleResponse:
    """Change a platform role through PostgreSQL-backed authorization only."""
    user = await change_platform_role(
        session,
        actor=ctx.user,
        target_user_id=user_id,
        new_role=payload.role,
    )
    await session.commit()
    return PlatformUserRoleResponse(
        user_id=str(user.id),
        cognito_sub=user.cognito_sub,
        email=user.email,
        platform_role=user.role.value,
    )
