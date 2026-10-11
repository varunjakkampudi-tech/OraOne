"""Phase 12 Module 4 — RBAC API.

Lightweight, read-only endpoints that expose the permission matrix so the
frontend can gate UI and so integrators can introspect their role's
capabilities. Authorisation enforcement happens at each guarded endpoint
via ``require_permission`` — these routes only *describe* access.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.permissions import (
    ALL_PERMISSIONS,
    permissions_for,
    role_matrix,
)
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.rbac import MyPermissionsResponse, RoleMatrixResponse

router = APIRouter(tags=["rbac"])


@router.get("/api/rbac/me", response_model=MyPermissionsResponse)
async def my_permissions(
    ctx: OrgContext = Depends(get_current_organization),
) -> MyPermissionsResponse:
    """Return the caller's role and the permissions it grants."""
    return MyPermissionsResponse(
        role=ctx.membership_role,
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
