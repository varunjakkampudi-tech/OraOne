"""Webhook management endpoints (R7 developer platform, dashboard-auth).

* ``GET    /api/webhooks``                  — list endpoints + event catalogue.
* ``POST   /api/webhooks``                  — create an endpoint (secret shown once).
* ``PATCH  /api/webhooks/{id}``             — update url/events/status/description.
* ``DELETE /api/webhooks/{id}``             — remove an endpoint.
* ``POST   /api/webhooks/{id}/rotate``      — rotate the signing secret.
* ``POST   /api/webhooks/{id}/test``        — send a synchronous test delivery.
* ``GET    /api/webhooks/{id}/deliveries``  — recent delivery attempts.

The programmatic surface (``/api/v1``) *fires* these; this router *manages* them
and is gated by the ``apikeys.manage`` / ``apikeys.read`` permissions.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.session import get_db
from app.middleware.org_context import OrgContext, require_permission
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.webhooks import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookDeliveryOut,
    WebhookEventInfo,
    WebhookListResponse,
    WebhookOut,
    WebhookUpdateRequest,
)
from app.services import webhook_service
from app.services.audit import audit

router = APIRouter(tags=["webhooks"])


@router.get("/api/webhooks", response_model=WebhookListResponse)
async def list_webhooks(
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WebhookListResponse:
    endpoints = await webhook_service.list_endpoints(
        session, ctx.organization_id, pctx.project_id
    )
    return WebhookListResponse(
        webhooks=[WebhookOut.model_validate(e) for e in endpoints],
        events=[WebhookEventInfo(**e) for e in webhook_service.event_catalogue()],
    )


@router.post(
    "/api/webhooks",
    response_model=WebhookCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_webhook(
    payload: WebhookCreateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WebhookCreateResponse:
    endpoint = await webhook_service.create_endpoint(
        session,
        organization_id=ctx.organization_id,
        url=payload.url,
        events=payload.events,
        description=payload.description,
        created_by_user_id=ctx.user_id,
        project_id=pctx.project_id,
    )
    await session.commit()
    audit(
        "create",
        resource="webhook_endpoint",
        resource_id=str(endpoint.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"url": endpoint.url, "events": endpoint.events},
    )
    return WebhookCreateResponse(
        webhook=WebhookOut.model_validate(endpoint),
        secret=endpoint.secret,
    )


async def _require_endpoint(session: AsyncSession, ctx: OrgContext, endpoint_id: uuid.UUID):
    endpoint = await webhook_service.get_endpoint(session, ctx.organization_id, endpoint_id)
    if endpoint is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found.")
    return endpoint


@router.patch("/api/webhooks/{endpoint_id}", response_model=WebhookOut)
async def update_webhook(
    endpoint_id: uuid.UUID,
    payload: WebhookUpdateRequest,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> WebhookOut:
    endpoint = await _require_endpoint(session, ctx, endpoint_id)
    await webhook_service.update_endpoint(
        session,
        endpoint,
        url=payload.url,
        events=payload.events,
        description=payload.description,
        status=payload.status,
    )
    await session.commit()
    return WebhookOut.model_validate(endpoint)


@router.delete("/api/webhooks/{endpoint_id}")
async def delete_webhook(
    endpoint_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    endpoint = await _require_endpoint(session, ctx, endpoint_id)
    await webhook_service.delete_endpoint(session, endpoint)
    await session.commit()
    audit(
        "delete",
        resource="webhook_endpoint",
        resource_id=str(endpoint_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return {"status": "deleted", "id": str(endpoint_id)}


@router.post("/api/webhooks/{endpoint_id}/rotate", response_model=WebhookCreateResponse)
async def rotate_webhook_secret(
    endpoint_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> WebhookCreateResponse:
    endpoint = await _require_endpoint(session, ctx, endpoint_id)
    await webhook_service.rotate_secret(session, endpoint)
    await session.commit()
    return WebhookCreateResponse(
        webhook=WebhookOut.model_validate(endpoint),
        secret=endpoint.secret,
    )


@router.post("/api/webhooks/{endpoint_id}/test", response_model=WebhookDeliveryOut)
async def test_webhook(
    endpoint_id: uuid.UUID,
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> WebhookDeliveryOut:
    endpoint = await _require_endpoint(session, ctx, endpoint_id)
    delivery = await webhook_service.send_test(session, endpoint)
    await session.commit()
    return WebhookDeliveryOut.model_validate(delivery)


@router.get("/api/webhooks/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryOut])
async def webhook_deliveries(
    endpoint_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    ctx: OrgContext = Depends(require_permission(Permission.APIKEYS_READ)),
    session: AsyncSession = Depends(get_db),
) -> list[WebhookDeliveryOut]:
    await _require_endpoint(session, ctx, endpoint_id)
    deliveries = await webhook_service.list_deliveries(
        session, ctx.organization_id, endpoint_id=endpoint_id, limit=limit
    )
    return [WebhookDeliveryOut.model_validate(d) for d in deliveries]
