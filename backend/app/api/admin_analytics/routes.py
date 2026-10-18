"""Admin analytics API.

``GET /api/admin/analytics/overview`` returns platform-level aggregate counts
for platform super-admins and admins. It holds no customer content and no
personal data. See ``app.services.admin_analytics_service``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.platform_context import PlatformContext, require_platform_role
from app.services import admin_analytics_service

router = APIRouter(prefix="/api/admin/analytics", tags=["admin-analytics"])


@router.get("/overview")
async def admin_analytics_overview(
    ctx: PlatformContext = Depends(require_platform_role("super_admin", "admin")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await admin_analytics_service.platform_overview(db)
