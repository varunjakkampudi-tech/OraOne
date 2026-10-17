"""Admin configuration console: read model, guarded writes and audit.

Read rules:
  * Secrets are never returned in full. The API returns set / not set and a
    masked tail of at most four characters.
  * Plain values are returned only for the ``local`` environment. Production
    values are never returned; production shows set / not set.
  * A deployment only knows its own process environment. For the other
    environment, only console-stored rows are visible, and the source says so.

Write rules:
  * The caller must be a super-admin (enforced by the router dependency).
  * The body must repeat the key name in ``confirm`` and give a ``reason``.
    Missing or wrong values are refused and the attempt is audited.
  * Every applied write and reload is audited with who, which key, when and
    why. Secret values never appear in audit records. Plain values appear as
    old and new values, as the console specification requires.
  * Changes take effect after a restart. The response and read model say so.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import config_overrides
from app.core.config_registry import (
    BY_NAME,
    ENVIRONMENTS,
    GROUPS,
    REGISTRY,
    ConfigKey,
    mask_secret,
    runtime_environment,
)
from app.core.crypto import decrypt, encrypt
from app.database.models.admin_config_override import AdminConfigOverride
from app.services.audit import audit, flush_pending

log = logging.getLogger("app.config_console")

AUDIT_RESOURCE = "admin_config"
PLATFORM_ORG = "platform"
MAX_VALUE_LENGTH = 2048
MIN_REASON_LENGTH = 10
MAX_REASON_LENGTH = 500
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


class ConfigConsoleError(Exception):
    """A request the console refuses. ``status`` is the HTTP status to return."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class AuditContext:
    actor_id: str
    actor_email: str
    ip: Optional[str] = None
    request_id: Optional[str] = None


def current_environment() -> str:
    return runtime_environment(os.environ.get("ENVIRONMENT"))


def _decrypt_row(row: AdminConfigOverride) -> Optional[str]:
    """Return the stored plaintext, or None when it cannot be read (no key, wrong key)."""
    try:
        return decrypt(row.value_encrypted)
    except RuntimeError:
        # The encryption key is not configured on this server.
        return None


async def _fetch_rows(
    session: AsyncSession, environment: str
) -> list[AdminConfigOverride]:
    result = await session.execute(
        select(AdminConfigOverride).where(
            AdminConfigOverride.environment == environment
        )
    )
    return list(result.scalars().all())


async def _upsert_row(
    session: AsyncSession,
    *,
    existing: Optional[AdminConfigOverride],
    environment: str,
    name: str,
    value_encrypted: str,
    actor_id: str,
    now: datetime,
) -> None:
    if existing is None:
        session.add(
            AdminConfigOverride(
                environment=environment,
                name=name,
                value_encrypted=value_encrypted,
                updated_by=_uuid_or_none(actor_id),
                updated_at=now,
            )
        )
    else:
        existing.value_encrypted = value_encrypted
        existing.updated_by = _uuid_or_none(actor_id)
        existing.updated_at = now


async def _delete_row(session: AsyncSession, *, environment: str, name: str) -> None:
    await session.execute(
        delete(AdminConfigOverride).where(
            AdminConfigOverride.environment == environment,
            AdminConfigOverride.name == name,
        )
    )


def _uuid_or_none(value: str) -> Any:
    import uuid

    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        return None


def _validate_value(value: str) -> str:
    if not isinstance(value, str):
        raise ConfigConsoleError(400, "Value must be text.")
    if len(value) > MAX_VALUE_LENGTH:
        raise ConfigConsoleError(
            400, f"Value must be {MAX_VALUE_LENGTH} characters or fewer."
        )
    if _CONTROL_CHARS.search(value):
        raise ConfigConsoleError(
            400, "Value must not contain line breaks or control characters."
        )
    if not value.strip():
        raise ConfigConsoleError(
            400, "Value is empty. Send null to remove the console value."
        )
    return value.strip()


def _audit_rejected(
    ctx: AuditContext, *, environment: Optional[str], name: str, code: str
) -> None:
    """Record a refused write. No value of any kind is recorded."""
    audit(
        "config_write_rejected",
        resource=AUDIT_RESOURCE,
        resource_id=f"{environment or '?'}:{name}",
        organization_id=PLATFORM_ORG,
        user_id=ctx.actor_id,
        meta={
            "admin_email": ctx.actor_email,
            "environment": environment,
            "key": name,
            "reason_code": code,
            "ip": ctx.ip,
            "request_id": ctx.request_id,
        },
    )


def _reject(
    ctx: AuditContext,
    *,
    environment: Optional[str],
    name: str,
    status: int,
    code: str,
    message: str,
) -> ConfigConsoleError:
    _audit_rejected(ctx, environment=environment, name=name, code=code)
    return ConfigConsoleError(status, message)


async def list_config(
    session: AsyncSession, *, environment: Optional[str] = None
) -> dict[str, Any]:
    """Return the registry with per-environment status. Never returns secrets."""
    runtime = current_environment()
    env = environment or runtime
    if env not in ENVIRONMENTS:
        raise ConfigConsoleError(400, "Environment must be local or production.")
    visible = env == runtime

    rows = {row.name: row for row in await _fetch_rows(session, env)}
    restart_required = False
    if env == runtime:
        restart_required = any(
            row.updated_at is not None
            and row.updated_at > config_overrides.PROCESS_STARTED_AT
            for row in rows.values()
        )
    else:
        runtime_rows = await _fetch_rows(session, runtime)
        restart_required = any(
            row.updated_at is not None
            and row.updated_at > config_overrides.PROCESS_STARTED_AT
            for row in runtime_rows
        )

    items: list[dict[str, Any]] = []
    for key in REGISTRY:
        if env not in key.environments:
            continue
        row = rows.get(key.name)
        deployment_value = os.environ.get(key.name) if visible else None
        stored_value = _decrypt_row(row) if row is not None else None

        if row is not None:
            is_set = True
            source = "console"
            effective: Optional[str] = stored_value
        elif visible and deployment_value:
            is_set = True
            source = "deployment"
            effective = deployment_value
        else:
            is_set = False
            source = "unknown" if not visible else "not_set"
            effective = None

        item: dict[str, Any] = {
            "name": key.name,
            "group": key.group,
            "kind": key.kind,
            "required": key.required,
            "description": key.description,
            "console_managed": key.console_managed,
            "is_set": is_set,
            "source": source,
            "overridden": row is not None,
        }
        if key.kind == "secret":
            item["masked_tail"] = mask_secret(effective) if is_set else None
            item["value"] = None
        else:
            item["masked_tail"] = None
            show_plain = env == "local" and is_set
            item["value"] = effective if show_plain else None
        items.append(item)

    return {
        "environment": env,
        "runtime_environment": runtime,
        "deployment_visible": visible,
        "restart_required": restart_required,
        "groups": list(GROUPS),
        "items": items,
    }


async def set_override(
    session: AsyncSession,
    *,
    ctx: AuditContext,
    environment: str,
    name: str,
    value: Optional[str],
    confirm: Optional[str],
    reason: Optional[str],
) -> dict[str, Any]:
    """Save, or with ``value=None`` remove, one console value for one environment."""
    key: Optional[ConfigKey] = BY_NAME.get(name)
    if key is None:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=404,
            code="unknown_key",
            message="Unknown configuration key.",
        )
    if environment not in ENVIRONMENTS:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="bad_environment",
            message="Environment must be local or production.",
        )
    if environment not in key.environments:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="not_applicable",
            message="This key does not apply to that environment.",
        )
    if not key.console_managed:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="not_console_managed",
            message="This key is managed outside the console and is read-only here.",
        )
    if confirm != name:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="confirm_mismatch",
            message="Type the exact key name in the confirm field.",
        )
    clean_reason = (reason or "").strip()
    if len(clean_reason) < MIN_REASON_LENGTH or len(clean_reason) > MAX_REASON_LENGTH:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="reason_length",
            message=f"Give a reason of {MIN_REASON_LENGTH} to {MAX_REASON_LENGTH} characters.",
        )
    clean_value: Optional[str] = None
    if value is not None:
        try:
            clean_value = _validate_value(value)
        except ConfigConsoleError as exc:
            raise _reject(
                ctx,
                environment=environment,
                name=name,
                status=exc.status,
                code="invalid_value",
                message=exc.message,
            ) from exc

    rows = await _fetch_rows(session, environment)
    row = next((r for r in rows if r.name == name), None)
    before_set = row is not None
    old_plain = _decrypt_row(row) if (row is not None and key.kind == "plain") else None

    if clean_value is None:
        if row is None:
            # Nothing to remove. Record the request so the attempt is visible.
            _audit_change(
                ctx,
                key,
                environment,
                action="delete",
                before={"set": False},
                after={"set": False},
                reason=clean_reason,
                outcome="no_change",
            )
            await flush_pending(session)
            return {
                "name": name,
                "environment": environment,
                "status": "unchanged",
                "restart_required": False,
            }
        await _delete_row(session, environment=environment, name=name)
        new_set = False
        new_plain: Optional[str] = None
        action = "delete"
        status = "cleared"
    else:
        try:
            encrypted = encrypt(clean_value)
        except RuntimeError as exc:
            raise ConfigConsoleError(
                503, "The encryption key is not configured on this server."
            ) from exc
        await _upsert_row(
            session,
            existing=row,
            environment=environment,
            name=name,
            value_encrypted=encrypted or "",
            actor_id=ctx.actor_id,
            now=datetime.now(timezone.utc),
        )
        new_set = True
        new_plain = clean_value
        action = "update"
        status = "saved"

    await session.commit()

    if key.kind == "plain":
        before = {"set": before_set, "value": old_plain}
        after = {"set": new_set, "value": new_plain}
    else:
        before = {"set": before_set}
        after = {"set": new_set}
    _audit_change(
        ctx,
        key,
        environment,
        action=action,
        before=before,
        after=after,
        reason=clean_reason,
        outcome="applied",
    )
    await flush_pending(session)
    log.info("config console: %s %s:%s by %s", status, environment, name, ctx.actor_id)
    return {
        "name": name,
        "environment": environment,
        "status": status,
        "restart_required": True,
    }


def _audit_change(
    ctx: AuditContext,
    key: ConfigKey,
    environment: str,
    *,
    action: str,
    before: dict[str, Any],
    after: dict[str, Any],
    reason: str,
    outcome: str,
) -> None:
    audit(
        action,
        resource=AUDIT_RESOURCE,
        resource_id=f"{environment}:{key.name}",
        organization_id=PLATFORM_ORG,
        user_id=ctx.actor_id,
        before=before,
        after=after,
        meta={
            "admin_email": ctx.actor_email,
            "environment": environment,
            "key": key.name,
            "kind": key.kind,
            "reason": reason,
            "outcome": outcome,
            "ip": ctx.ip,
            "request_id": ctx.request_id,
        },
    )


async def reload_overrides(
    ctx: AuditContext, *, confirm: Optional[str], reason: Optional[str]
) -> dict[str, Any]:
    """Re-read stored values into this process. Other workers keep their values until restart."""
    clean_reason = (reason or "").strip()
    if len(clean_reason) < MIN_REASON_LENGTH or len(clean_reason) > MAX_REASON_LENGTH:
        raise _reject(
            ctx,
            environment=None,
            name="reload",
            status=400,
            code="reason_length",
            message=f"Give a reason of {MIN_REASON_LENGTH} to {MAX_REASON_LENGTH} characters.",
        )
    if confirm != "RELOAD":
        raise _reject(
            ctx,
            environment=None,
            name="reload",
            status=400,
            code="confirm_mismatch",
            message="Type RELOAD in the confirm field.",
        )
    try:
        changed = await config_overrides.reload_stored_overrides()
    except Exception as exc:
        audit(
            "reload_failed",
            resource=AUDIT_RESOURCE,
            resource_id=f"{current_environment()}:reload",
            organization_id=PLATFORM_ORG,
            user_id=ctx.actor_id,
            meta={
                "admin_email": ctx.actor_email,
                "error_type": type(exc).__name__,
                "reason": clean_reason,
                "ip": ctx.ip,
                "request_id": ctx.request_id,
            },
        )
        raise ConfigConsoleError(503, "Reload failed. Check the server logs.") from exc
    audit(
        "reload",
        resource=AUDIT_RESOURCE,
        resource_id=f"{current_environment()}:reload",
        organization_id=PLATFORM_ORG,
        user_id=ctx.actor_id,
        meta={
            "admin_email": ctx.actor_email,
            "changed_keys": sorted(changed),
            "reason": clean_reason,
            "ip": ctx.ip,
            "request_id": ctx.request_id,
        },
    )
    return {
        "status": "reloaded",
        "changed_keys": sorted(changed),
        "note": "This process only. Restart all workers to apply every change.",
    }
