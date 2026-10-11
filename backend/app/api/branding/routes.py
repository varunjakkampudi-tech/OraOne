"""Phase 12 Module 15 — White-label branding API.

* ``GET  /api/branding``          — current org branding + plan gating.
* ``PUT  /api/branding``          — update branding (validated, plan-gated).
* ``GET  /api/public/branding``   — public-safe branding by org slug/id
  (no auth) for white-labelling customer-facing surfaces.

Reads require ``settings.read``; updates require ``settings.manage``.
"""
from __future__ import annotations

import io
import os
import re
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.session import get_db
from app.middleware.org_context import OrgContext, require_permission
from app.schemas.branding import BrandingUpdate, BrandingView, PublicBranding
from app.services import branding_service, storage
from app.services.audit import audit

router = APIRouter(tags=["branding"])

# Uploaded brand assets: small images only.
_MAX_ASSET_BYTES = 2 * 1024 * 1024  # 2 MB
_ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/svg+xml": "svg",
    "image/webp": "webp",
    "image/gif": "gif",
}
# Keys we are willing to serve back: org/<uuid>/branding/<uuid>__<safe-name>
_ASSET_KEY_RE = re.compile(r"^org/[0-9a-fA-F-]{36}/branding/[A-Za-z0-9._-]+$")


def _public_base() -> str:
    """Absolute, externally-reachable base URL for serving brand assets."""
    base = (
        os.environ.get("BACKEND_PUBLIC_URL")
        or os.environ.get("PUBLIC_BACKEND_URL")
        or os.environ.get("BACKEND_URL")
        or "http://localhost:8000"
    )
    return base.rstrip("/")



@router.get("/api/branding", response_model=BrandingView)
async def get_branding(
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_READ)),
    session: AsyncSession = Depends(get_db),
) -> BrandingView:
    view = await branding_service.branding_view(session, ctx.organization_id)
    return BrandingView(**view)


@router.put("/api/branding", response_model=BrandingView)
async def update_branding(
    payload: BrandingUpdate,
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> BrandingView:
    await branding_service.update_branding(
        session,
        ctx.organization_id,
        brand_name=payload.brand_name,
        logo_url=payload.logo_url,
        icon_url=payload.icon_url,
        primary_color=payload.primary_color,
        accent_color=payload.accent_color,
        support_email=payload.support_email,
        support_url=payload.support_url,
        custom_domain=payload.custom_domain,
        hide_powered_by=payload.hide_powered_by,
    )
    audit(
        "update",
        resource="org_branding",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"brand_name": payload.brand_name, "primary_color": payload.primary_color},
    )
    view = await branding_service.branding_view(session, ctx.organization_id)
    return BrandingView(**view)


async def _upload_brand_asset(
    *, field: str, file: UploadFile, ctx: OrgContext, session: AsyncSession
) -> BrandingView:
    ext = _ALLOWED_IMAGE_TYPES.get((file.content_type or "").lower())
    if not ext:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a PNG, JPG, SVG, WEBP or GIF image.",
        )
    body = await file.read()
    if len(body) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(body) > _MAX_ASSET_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image must be 2 MB or smaller.",
        )

    key = f"org/{ctx.organization_id}/branding/{uuid.uuid4().hex}__{field}.{ext}"
    storage.put_object(key=key, body=io.BytesIO(body), content_type=file.content_type)
    public_url = f"{_public_base()}/api/branding/asset/{key}"

    await branding_service.set_branding_asset(
        session, ctx.organization_id, field=field, url=public_url
    )
    audit(
        "update",
        resource="org_branding",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={f"{field}_url": public_url},
    )
    view = await branding_service.branding_view(session, ctx.organization_id)
    return BrandingView(**view)


@router.post("/api/branding/logo", response_model=BrandingView)
async def upload_logo(
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
) -> BrandingView:
    return await _upload_brand_asset(field="logo", file=file, ctx=ctx, session=session)


@router.post("/api/branding/icon", response_model=BrandingView)
async def upload_icon(
    file: UploadFile = File(...),
    ctx: OrgContext = Depends(require_permission(Permission.SETTINGS_MANAGE)),
    session: AsyncSession = Depends(get_db),
):
    return await _upload_brand_asset(field="icon", file=file, ctx=ctx, session=session)


@router.get("/api/branding/asset/{key:path}")
async def branding_asset(key: str):
    """Serve an uploaded brand asset (public — used by white-label surfaces)."""
    if not _ASSET_KEY_RE.match(key):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    # Local-disk mode: stream the file, guarding against path traversal.
    local = storage.local_path("local://" + key)
    root = storage._local_root().resolve()
    try:
        resolved = local.resolve()
    except OSError:
        resolved = local
    if str(resolved).startswith(str(root)) and resolved.is_file():
        return FileResponse(resolved)
    # S3 mode: stream the object back through the backend so the browser only
    # ever talks to our own origin (avoids S3 region/CORS/ORB pitfalls).
    obj = storage.get_object(key)
    if obj is not None:
        data, content_type = obj
        return Response(
            content=data,
            media_type=content_type or "application/octet-stream",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")


@router.get("/api/public/branding", response_model=PublicBranding)
async def public_branding(
    org: str = Query(..., description="Organization slug or UUID"),
    session: AsyncSession = Depends(get_db),
) -> PublicBranding:
    data = await branding_service.public_branding(session, org_ref=org)
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found."
        )
    return PublicBranding(**data)
