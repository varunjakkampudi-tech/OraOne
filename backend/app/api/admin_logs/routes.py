"""Admin log viewer API (platform ``super_admin`` or ``admin`` only).

* ``GET /api/admin/logs/errors`` — recent 5xx records, filtered by time range,
  route, status and request ID.
* ``GET /api/admin/logs/errors/{request_id}`` — one record with stack trace and
  the related JSON log lines from the app log file (when ``APP_LOG_FILE`` is set).
* ``GET /api/admin/logs/download`` — JSON or CSV for a time range, capped at
  ``EXPORT_ROW_CAP`` rows and streamed. Every download is audited.

Every response passes through the scrubbers in ``app.core.log_redaction``.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.platform_context import PlatformContext, require_platform_role
from app.services import error_events
from app.services.audit import audit, flush_pending

router = APIRouter(prefix="/api/admin/logs", tags=["admin-logs"])

REQUEST_ID_PATTERN = r"^[A-Za-z0-9._:-]{8,128}$"
_admin_only = require_platform_role("super_admin", "admin")


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _resolve_range(
    start: Optional[datetime], end: Optional[datetime]
) -> tuple[datetime, datetime]:
    """Default to the last 24 hours; refuse ranges past the retention window."""
    end_dt = _as_utc(end) if end else datetime.now(timezone.utc)
    start_dt = (
        _as_utc(start)
        if start
        else end_dt - timedelta(hours=error_events.DEFAULT_RANGE_HOURS)
    )
    if start_dt >= end_dt:
        raise HTTPException(status_code=422, detail="start must be before end.")
    if end_dt - start_dt > timedelta(days=error_events.MAX_RANGE_DAYS):
        raise HTTPException(
            status_code=422,
            detail=f"Ranges are limited to {error_events.MAX_RANGE_DAYS} days.",
        )
    return start_dt, end_dt


@router.get("/errors")
async def list_errors(
    start: Optional[datetime] = Query(
        None, description="ISO 8601; defaults to 24h before end"
    ),
    end: Optional[datetime] = Query(None, description="ISO 8601; defaults to now"),
    route: Optional[str] = Query(
        None, max_length=255, description="Route template fragment"
    ),
    status: Optional[int] = Query(None, ge=500, le=599),
    request_id: Optional[str] = Query(None, pattern=REQUEST_ID_PATTERN),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000),
    _ctx: PlatformContext = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    start_dt, end_dt = _resolve_range(start, end)
    rows, total = await error_events.list_error_events(
        db,
        start=start_dt,
        end=end_dt,
        route=route,
        status_code=status,
        request_id=request_id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [error_events.serialize_error_event(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "range": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
    }


@router.get("/errors/{request_id}")
async def get_error(
    request_id: str = Path(..., pattern=REQUEST_ID_PATTERN),
    _ctx: PlatformContext = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await error_events.get_error_event(db, request_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail="No error recorded for that request ID."
        )
    log_file = error_events.app_log_file()
    related = await asyncio.to_thread(
        error_events.read_related_log_lines, request_id, log_file
    )
    return {
        "error": error_events.serialize_error_event(row, include_stack=True),
        "related_logs": related,
        "log_file_configured": log_file is not None,
    }


@router.get("/download")
async def download_errors(
    format: Literal["json", "csv"] = Query("json"),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    route: Optional[str] = Query(None, max_length=255),
    status: Optional[int] = Query(None, ge=500, le=599),
    request_id: Optional[str] = Query(None, pattern=REQUEST_ID_PATTERN),
    ctx: PlatformContext = Depends(_admin_only),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    start_dt, end_dt = _resolve_range(start, end)
    rows, truncated = await error_events.export_error_events(
        db,
        start=start_dt,
        end=end_dt,
        route=route,
        status_code=status,
        request_id=request_id,
    )
    audit(
        "download",
        resource="error_logs",
        organization_id="platform",
        user_id=str(ctx.user.id),
        meta={
            "format": format,
            "range_start": start_dt.isoformat(),
            "range_end": end_dt.isoformat(),
            "route": route,
            "status_code": status,
            "request_id": request_id,
            "row_count": len(rows),
            "truncated": truncated,
        },
    )
    await flush_pending(db)

    generated_at = datetime.now(timezone.utc)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    extension = "json" if format == "json" else "csv"
    headers = {
        "Content-Disposition": f'attachment; filename="oraone-error-logs-{stamp}.{extension}"',
        "Cache-Control": "no-store",
        "X-Row-Cap": str(error_events.EXPORT_ROW_CAP),
        "X-Truncated": "true" if truncated else "false",
    }
    if format == "json":
        items = [
            error_events.serialize_error_event(r, include_stack=True) for r in rows
        ]
        body: AsyncIterator[str] = error_events.stream_json_export(
            items, truncated=truncated, generated_at=generated_at
        )
        return StreamingResponse(body, media_type="application/json", headers=headers)
    items = [error_events.serialize_error_event(r) for r in rows]
    return StreamingResponse(
        error_events.stream_csv_export(items),
        media_type="text/csv; charset=utf-8",
        headers=headers,
    )
