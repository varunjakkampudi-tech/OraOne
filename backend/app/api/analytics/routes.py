"""Phase 12 Module 6 + R8 — Organization analytics & observability API.

Org-scoped roll-ups powering the Analytics dashboards: an overview plus per
-module breakdowns (chat, agents, knowledge, RAG, widget, workflows,
integrations, cost, users, executive). Read access requires the
``analytics.read`` permission. Everything is computed live and strictly
scoped by ``organization_id``.
"""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.org_context import OrgContext, require_permission
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.analytics import OrgAnalyticsResponse
from app.services import analytics_service

router = APIRouter(tags=["analytics"])


@router.get("/api/analytics/overview", response_model=OrgAnalyticsResponse)
async def analytics_overview(
    days: int = Query(30, ge=1, le=90),
    ctx: OrgContext = Depends(require_permission("analytics.read")),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> OrgAnalyticsResponse:
    data = await analytics_service.org_overview(
        session, ctx.organization_id, days, project_id=pctx.project_id
    )
    return OrgAnalyticsResponse(**data)


@router.get("/api/analytics/modules")
async def analytics_modules(
    ctx: OrgContext = Depends(require_permission("analytics.read")),
) -> dict:
    """List the available analytics module keys."""
    return {"modules": sorted(analytics_service.MODULE_FUNCTIONS.keys())}


@router.get("/api/analytics/export")
async def analytics_export(
    module: str = Query("executive"),
    days: int = Query(30, ge=1, le=90),
    format: str = Query("json", pattern="^(json|csv)$"),
    ctx: OrgContext = Depends(require_permission("analytics.read")),
    session: AsyncSession = Depends(get_db),
):
    """Export a module's analytics as JSON or a flattened CSV of its KPIs."""
    fn = analytics_service.MODULE_FUNCTIONS.get(module) or (
        analytics_service.org_overview if module == "overview" else None
    )
    if fn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown module '{module}'.")
    data = await fn(session, ctx.organization_id, days)
    if format == "json":
        return data

    # CSV: flatten the top-level numeric "totals"/"kpis" maps.
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    for section in ("kpis", "totals"):
        for k, v in (data.get(section) or {}).items():
            if isinstance(v, (int, float, str)) or v is None:
                writer.writerow([f"{section}.{k}", v])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=oraone_{module}_{days}d.csv"},
    )


@router.get("/api/analytics/{module}")
async def analytics_module(
    module: str,
    days: int = Query(30, ge=1, le=90),
    ctx: OrgContext = Depends(require_permission("analytics.read")),
    session: AsyncSession = Depends(get_db),
) -> dict:
    fn = analytics_service.MODULE_FUNCTIONS.get(module)
    if fn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown analytics module '{module}'."
        )
    return await fn(session, ctx.organization_id, days)
