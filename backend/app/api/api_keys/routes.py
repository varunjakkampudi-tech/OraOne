"""Phase 12 Module 9 — API key management (dashboard, Cognito-auth).

* ``GET    /api/api-keys``          — list keys + available scopes.
* ``POST   /api/api-keys``          — create a key (secret shown once).
* ``DELETE /api/api-keys/{key_id}`` — revoke a key.

These are management endpoints used by the in-app dashboard and are gated
by the RBAC permissions ``apikeys.read`` / ``apikeys.manage``. The external
programmatic surface authenticated *by* API keys lives under ``/api/v1``.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.api_scopes import scope_catalogue
from app.core.permissions import Permission
from app.database.session import get_db
from app.middleware.org_context import OrgContext, require_permission
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.api_keys import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyListResponse,
    ApiKeyOut,
    ScopeOption,
)
from app.services import api_key_service
from app.services.audit import audit

router = APIRouter(tags=["api-keys"])


@router.get("/api/api-keys", response_model=ApiKeyListResponse)
async def list_api_keys(
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyListResponse:
    keys = await api_key_service.list_keys(session, ctx.organization_id, pctx.project_id)
    return ApiKeyListResponse(
        keys=[ApiKeyOut.model_validate(k) for k in keys],
        scopes=[ScopeOption(**s) for s in scope_catalogue()],
    )


@router.post(
    "/api/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_api_key(
    payload: ApiKeyCreateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> ApiKeyCreateResponse:
    row, full_key = await api_key_service.create_key(
        session,
        ctx.organization_id,
        name=payload.name,
        scopes=payload.scopes,
        created_by_user_id=ctx.user_id,
        expires_at=payload.expires_at,
        project_id=pctx.project_id,
    )
    audit(
        "create",
        resource="api_key",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"name": row.name, "scopes": row.scopes},
    )
    return ApiKeyCreateResponse(key=full_key, api_key=ApiKeyOut.model_validate(row))


@router.delete("/api/api-keys/{key_id}")
async def revoke_api_key(
    key_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    row = await api_key_service.revoke_key(session, ctx.organization_id, key_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="API key not found."
        )
    audit(
        "delete",
        resource="api_key",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"name": row.name},
    )
    return {"status": "revoked", "id": str(row.id)}
