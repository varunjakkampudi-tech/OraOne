"""Admin configuration console API.

Super-admin only. Reads never return a secret in full. Writes require the
exact key name in ``confirm`` and a ``reason``; refused attempts are audited.
Changes take effect after a restart.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.platform_context import PlatformContext, require_platform_role
from app.services import config_console as console
from app.services.audit import flush_pending

router = APIRouter(prefix="/api/admin/config", tags=["admin-config"])

_NAME_PATTERN = r"^[A-Z][A-Z0-9_]{1,79}$"


class ConfigWriteRequest(BaseModel):
    environment: Literal["local", "production"]
    value: Optional[str] = Field(
        default=None,
        max_length=console.MAX_VALUE_LENGTH,
        description="New value. Send null to remove the console value.",
    )
    confirm: Optional[str] = Field(default=None, max_length=120)
    reason: Optional[str] = Field(default=None, max_length=1000)


class ReloadRequest(BaseModel):
    confirm: Optional[str] = Field(default=None, max_length=20)
    reason: Optional[str] = Field(default=None, max_length=1000)


def _context(ctx: PlatformContext, request: Request) -> console.AuditContext:
    return console.AuditContext(
        actor_id=str(ctx.user.id),
        actor_email=str(ctx.user.email),
        ip=request.client.host if request.client else None,
        request_id=request.headers.get("x-request-id"),
    )


async def _refuse(db: AsyncSession, exc: console.ConfigConsoleError) -> None:
    """Persist the audit record of a refused request, then return the HTTP error."""
    await flush_pending(db)
    raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.get("")
async def list_configuration(
    environment: Optional[Literal["local", "production"]] = Query(None),
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await console.list_config(db, environment=environment)
    except console.ConfigConsoleError as exc:
        await _refuse(db, exc)
        raise  # pragma: no cover


@router.post("/reload")
async def reload_configuration(
    payload: ReloadRequest,
    request: Request,
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        result = await console.reload_overrides(
            _context(ctx, request),
            confirm=payload.confirm,
            reason=payload.reason,
        )
    except console.ConfigConsoleError as exc:
        await _refuse(db, exc)
        raise  # pragma: no cover
    await flush_pending(db)
    return result


@router.put("/{name}")
async def write_configuration(
    payload: ConfigWriteRequest,
    request: Request,
    name: str = Path(..., pattern=_NAME_PATTERN),
    ctx: PlatformContext = Depends(require_platform_role("super_admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        return await console.set_override(
            db,
            ctx=_context(ctx, request),
            environment=payload.environment,
            name=name,
            value=payload.value,
            confirm=payload.confirm,
            reason=payload.reason,
        )
    except console.ConfigConsoleError as exc:
        await _refuse(db, exc)
        raise  # pragma: no cover
