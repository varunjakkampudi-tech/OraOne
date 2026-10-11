"""Phase 12 Module 2 — Usage metering API.

* ``GET  /api/usage``          — usage-vs-limits snapshot for the org.
* ``GET  /api/usage/check``    — quota check for a single metric.
* ``POST /api/usage/record``   — record a metered event (gated, mainly
  used by internal callers / instrumentation).

Reads only require org membership. Recording requires ``billing.read``
(any active member except viewers can be wired later; for now we accept
authenticated org context and rely on the metric registry to ignore
unknown metrics).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.usage import (
    QuotaCheckResponse,
    RecordUsageRequest,
    RecordUsageResponse,
    UsageSnapshotResponse,
)
from app.services import usage_service

router = APIRouter(tags=["usage"])


@router.get("/api/usage", response_model=UsageSnapshotResponse)
async def get_usage(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> UsageSnapshotResponse:
    snapshot = await usage_service.usage_snapshot(session, ctx.organization_id)
    return UsageSnapshotResponse(**snapshot)


@router.get("/api/usage/check", response_model=QuotaCheckResponse)
async def check_usage(
    metric: str = Query(..., min_length=1, max_length=60),
    amount: int = Query(1, ge=1, le=10000),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> QuotaCheckResponse:
    result = await usage_service.check_quota(
        session, ctx.organization_id, metric, amount
    )
    return QuotaCheckResponse(**result)


@router.post("/api/usage/record", response_model=RecordUsageResponse)
async def record_usage(
    payload: RecordUsageRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RecordUsageResponse:
    total = await usage_service.record_usage(
        session, ctx.organization_id, payload.metric, payload.amount
    )
    return RecordUsageResponse(metric=payload.metric, period_total=total)
