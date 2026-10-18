"""Structured error store and export for the admin log viewer.

Flow: ``app.middleware.request_context`` calls :func:`record_failure` for every
5xx response and unhandled exception. That builds a scrubbed record, writes one
``error_events`` row, and emits one ``request.error`` log line carrying the same
request ID the caller received.

Everything here is best-effort on the write path: a failed insert is logged and
never changes the response the caller gets.
"""

from __future__ import annotations

import csv
import io
import json
import os
import traceback
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Iterable, Optional

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.log_redaction import format_frames, replace_raw_path, scrub_text
from app.database.models.error_event import ErrorEvent

log = structlog.get_logger("app.errors")

#: Hard cap on rows in one download. Larger ranges must be split by the caller.
EXPORT_ROW_CAP = 10_000
#: Keep a bounded window of records per request; the store itself is pruned at 30 days.
MAX_RANGE_DAYS = 30
DEFAULT_RANGE_HOURS = 24

MESSAGE_LIMIT = 300
STACK_LIMIT = 4000

#: Release identifier stamped on every record. Set ``ORAONE_RELEASE`` at deploy time.
RELEASE_VERSION = (
    os.environ.get("ORAONE_RELEASE") or os.environ.get("ORAONE_VERSION") or "2.0.0"
)[:64]

_CSV_COLUMNS = (
    "occurred_at",
    "request_id",
    "method",
    "route",
    "status_code",
    "duration_ms",
    "exception_type",
    "message",
    "release_version",
    "trace_id",
    "actor_hash",
    "org_hash",
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_error_event(
    *,
    request_id: str,
    method: str,
    route: str,
    status_code: int,
    duration_ms: int,
    exc: BaseException | None,
    raw_path: str | None = None,
    trace_id: str | None = None,
    actor_hash: str | None = None,
    org_hash: str | None = None,
    occurred_at: datetime | None = None,
) -> dict[str, Any]:
    """Return column values for one ``error_events`` row. Pure: no I/O.

    The message and stack are scrubbed here, so nothing downstream ever receives
    raw personal data or a concrete path that may carry a token.
    """
    exception_type: str | None = None
    message: str | None = None
    stack: str | None = None
    if exc is not None:
        exception_type = type(exc).__name__[:120]
        raw_message = replace_raw_path(str(exc), raw_path, route)
        message = scrub_text(raw_message or exception_type, limit=MESSAGE_LIMIT)
        frames = [
            (frame.filename, frame.lineno or 0, frame.name)
            for frame in traceback.extract_tb(exc.__traceback__)
        ]
        lines = format_frames(frames)
        lines.append(f"{exception_type}: {message}")
        stack = scrub_text("\n".join(lines), limit=STACK_LIMIT)
    else:
        message = f"HTTP {status_code} response"

    return {
        "request_id": request_id[:128],
        "occurred_at": occurred_at or _utcnow(),
        "method": method[:12],
        "route": route[:255],
        "status_code": int(status_code),
        "duration_ms": max(0, int(duration_ms)),
        "exception_type": exception_type,
        "message": message,
        "stack_trace": stack,
        "release_version": RELEASE_VERSION,
        "trace_id": (trace_id or None) and str(trace_id)[:64],
        "actor_hash": (actor_hash or None) and str(actor_hash)[:32],
        "org_hash": (org_hash or None) and str(org_hash)[:32],
    }


async def persist_error_event(data: dict[str, Any]) -> bool:
    """Insert one row. Returns False (and logs) when the store is unavailable."""
    try:
        from app.database import session as db_session

        factory = db_session.AsyncSessionLocal
        if factory is None:
            return False
        async with factory() as session:
            session.add(ErrorEvent(**data))
            await session.commit()
        return True
    except Exception as exc:  # noqa: BLE001 — recording must never fail a request
        log.warning("error_event.persist_failed", error_type=type(exc).__name__)
        return False


async def record_failure(**kwargs: Any) -> dict[str, Any]:
    """Build, store and log one server error. Never raises."""
    try:
        data = build_error_event(**kwargs)
    except Exception as exc:  # noqa: BLE001
        log.warning("error_event.build_failed", error_type=type(exc).__name__)
        return {}
    log.error(
        "request.error",
        request_id=data["request_id"],
        route=data["route"],
        method=data["method"],
        status_code=data["status_code"],
        duration_ms=data["duration_ms"],
        exception_type=data["exception_type"],
        message=data["message"],
        trace_id=data["trace_id"],
        actor_hash=data["actor_hash"],
        org_hash=data["org_hash"],
    )
    await persist_error_event(data)
    return data


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _filtered(
    stmt,
    *,
    start: Optional[datetime],
    end: Optional[datetime],
    route: Optional[str],
    status_code: Optional[int],
    request_id: Optional[str],
):
    if start is not None:
        stmt = stmt.where(ErrorEvent.occurred_at >= start)
    if end is not None:
        stmt = stmt.where(ErrorEvent.occurred_at < end)
    if route:
        stmt = stmt.where(
            ErrorEvent.route.ilike(f"%{_escape_like(route)}%", escape="\\")
        )
    if status_code is not None:
        stmt = stmt.where(ErrorEvent.status_code == status_code)
    if request_id:
        stmt = stmt.where(ErrorEvent.request_id == request_id)
    return stmt


async def list_error_events(
    session: AsyncSession,
    *,
    start: Optional[datetime],
    end: Optional[datetime],
    route: Optional[str] = None,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ErrorEvent], int]:
    base = _filtered(
        select(ErrorEvent),
        start=start,
        end=end,
        route=route,
        status_code=status_code,
        request_id=request_id,
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = (
        await session.scalars(
            base.order_by(ErrorEvent.occurred_at.desc(), ErrorEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows), int(total or 0)


async def get_error_event(session: AsyncSession, request_id: str) -> ErrorEvent | None:
    return await session.scalar(
        select(ErrorEvent)
        .where(ErrorEvent.request_id == request_id)
        .order_by(ErrorEvent.occurred_at.desc())
        .limit(1)
    )


async def export_error_events(
    session: AsyncSession,
    *,
    start: Optional[datetime],
    end: Optional[datetime],
    route: Optional[str] = None,
    status_code: Optional[int] = None,
    request_id: Optional[str] = None,
) -> tuple[list[ErrorEvent], bool]:
    """Up to ``EXPORT_ROW_CAP`` rows, oldest first, plus whether more matched."""
    stmt = _filtered(
        select(ErrorEvent),
        start=start,
        end=end,
        route=route,
        status_code=status_code,
        request_id=request_id,
    )
    rows = (
        await session.scalars(
            stmt.order_by(ErrorEvent.occurred_at.asc(), ErrorEvent.id.asc()).limit(
                EXPORT_ROW_CAP + 1
            )
        )
    ).all()
    truncated = len(rows) > EXPORT_ROW_CAP
    return list(rows[:EXPORT_ROW_CAP]), truncated


# ---------------------------------------------------------------------------
# Serialisation (redacted on the way out, as well as on the way in)
# ---------------------------------------------------------------------------


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def serialize_error_event(
    row: ErrorEvent, *, include_stack: bool = False
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(row.id),
        "request_id": row.request_id,
        "occurred_at": _iso(row.occurred_at),
        "method": row.method,
        "route": scrub_text(row.route, limit=255),
        "status_code": row.status_code,
        "duration_ms": row.duration_ms,
        "exception_type": scrub_text(row.exception_type, limit=120)
        if row.exception_type
        else None,
        "message": scrub_text(row.message, limit=MESSAGE_LIMIT)
        if row.message
        else None,
        "release_version": row.release_version,
        "trace_id": row.trace_id,
        "actor_hash": row.actor_hash,
        "org_hash": row.org_hash,
    }
    if include_stack:
        out["stack_trace"] = (
            scrub_text(row.stack_trace, limit=STACK_LIMIT) if row.stack_trace else None
        )
    return out


def _csv_safe(value: Any) -> str:
    """Neutralise spreadsheet formula injection (cells starting with = + - @)."""
    if value is None:
        return ""
    text = str(value)
    if text[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + text
    return text


def csv_header_line() -> str:
    buffer = io.StringIO()
    csv.writer(buffer).writerow(_CSV_COLUMNS)
    return buffer.getvalue()


def csv_row_line(item: dict[str, Any]) -> str:
    buffer = io.StringIO()
    csv.writer(buffer).writerow(
        [_csv_safe(item.get(column)) for column in _CSV_COLUMNS]
    )
    return buffer.getvalue()


async def stream_json_export(
    items: Iterable[dict[str, Any]], *, truncated: bool, generated_at: datetime
) -> AsyncIterator[str]:
    yield (
        '{"generated_at":'
        + json.dumps(generated_at.isoformat())
        + ',"row_cap":'
        + str(EXPORT_ROW_CAP)
        + ',"truncated":'
        + ("true" if truncated else "false")
        + ',"items":['
    )
    first = True
    for item in items:
        yield ("" if first else ",") + json.dumps(item, default=str)
        first = False
    yield "]}"


async def stream_csv_export(
    items: Iterable[dict[str, Any]],
) -> AsyncIterator[str]:
    yield csv_header_line()
    for item in items:
        yield csv_row_line(item)


# ---------------------------------------------------------------------------
# Related log lines
# ---------------------------------------------------------------------------


def app_log_file() -> str | None:
    """Path of the JSON-lines application log, when the deployment writes one."""
    return os.environ.get("APP_LOG_FILE") or None


def _scrub_value(value: Any) -> Any:
    if isinstance(value, str):
        return scrub_text(value, limit=500)
    if isinstance(value, dict):
        return {str(k): _scrub_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_scrub_value(v) for v in value]
    return value


def read_related_log_lines(
    request_id: str,
    path: str | None,
    *,
    max_bytes: int = 5 * 1024 * 1024,
    max_lines: int = 200,
) -> list[dict[str, Any]]:
    """Log lines for one request, read from the tail of the app log file.

    Blocking file I/O: call it through ``asyncio.to_thread``.
    """
    if not path or not os.path.isfile(path):
        return []
    size = os.path.getsize(path)
    with open(path, "rb") as handle:
        handle.seek(max(0, size - max_bytes))
        data = handle.read()
    lines = data.decode("utf-8", errors="replace").splitlines()
    if size > max_bytes and lines:
        lines = lines[1:]  # the first line may start mid-record
    found: list[dict[str, Any]] = []
    for raw in lines:
        if request_id not in raw:
            continue
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("request_id") != request_id:
            continue
        found.append(_scrub_value(entry))
        if len(found) >= max_lines:
            break
    return found
