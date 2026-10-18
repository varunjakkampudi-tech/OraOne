"""Admin configuration console: read model, drafts, guarded publish and audit.

Read rules:
  * Secrets are never returned in full. The API returns set / not set and a
    masked tail of at most four characters.
  * Plain values are returned only for the ``local`` environment. Production
    values are never returned; production shows set / not set.
  * A deployment only knows its own process environment. For the other
    environment, only console-stored rows are visible, and the source says so.

Draft and publish rules:
  * Saving a change writes a draft (encrypted, per environment). A draft never
    changes the active configuration or the running application.
  * Only a super-admin can save, discard or publish drafts (enforced by the
    router dependency).
  * Publishing needs the environment name typed in ``confirm``, a reason of
    10 to 500 characters, and the list of draft keys the caller reviewed. It
    copies every draft into the active store in one transaction, then deletes
    the drafts and records a publish event with key names and change types.
  * The diff shown before publishing masks secrets. Production plain values
    are never shown.
  * Changes take effect after a restart. The response and read model say so.

Audit rules:
  * Every saved draft, discarded draft, publish and refused request is
    audited with who, which key or environment, when, and why.
  * Secret values never appear in audit records or publish events. Plain
    values are never written to the audit log by the draft or publish flow.
"""

from __future__ import annotations

import logging
import os
import re
import uuid
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
from app.database.models.admin_config_draft import AdminConfigDraft
from app.database.models.admin_config_override import AdminConfigOverride
from app.database.models.admin_config_publish_event import AdminConfigPublishEvent
from app.services.audit import audit, flush_pending

log = logging.getLogger("app.config_console")

AUDIT_RESOURCE = "admin_config"
PLATFORM_ORG = "platform"
MAX_VALUE_LENGTH = 2048
MIN_REASON_LENGTH = 10
MAX_REASON_LENGTH = 500
HISTORY_LIMIT = 50
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


def _decrypt_value(encrypted: Optional[str]) -> Optional[str]:
    """Return the stored plaintext, or None when it cannot be read (no key, wrong key)."""
    if not encrypted:
        return None
    try:
        return decrypt(encrypted)
    except RuntimeError:
        # The encryption key is not configured on this server.
        return None


# --------------------------------------------------------------------------- #
# Storage helpers. Each one is a single place to read or write a table, so   #
# tests can replace them with an in-memory store.                             #
# --------------------------------------------------------------------------- #
async def _fetch_rows(
    session: AsyncSession, environment: str
) -> list[AdminConfigOverride]:
    """Active (published) values for one environment."""
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


async def _fetch_drafts(
    session: AsyncSession, environment: str
) -> list[AdminConfigDraft]:
    """Pending drafts for one environment. Never read by the running application."""
    result = await session.execute(
        select(AdminConfigDraft).where(AdminConfigDraft.environment == environment)
    )
    return list(result.scalars().all())


async def _upsert_draft(
    session: AsyncSession,
    *,
    existing: Optional[AdminConfigDraft],
    environment: str,
    name: str,
    action: str,
    value_encrypted: Optional[str],
    actor_id: str,
    now: datetime,
) -> None:
    if existing is None:
        session.add(
            AdminConfigDraft(
                environment=environment,
                name=name,
                action=action,
                value_encrypted=value_encrypted,
                updated_by=_uuid_or_none(actor_id),
                updated_at=now,
            )
        )
    else:
        existing.action = action
        existing.value_encrypted = value_encrypted
        existing.updated_by = _uuid_or_none(actor_id)
        existing.updated_at = now


async def _delete_draft(session: AsyncSession, *, environment: str, name: str) -> None:
    await session.execute(
        delete(AdminConfigDraft).where(
            AdminConfigDraft.environment == environment,
            AdminConfigDraft.name == name,
        )
    )


async def _delete_drafts(session: AsyncSession, *, environment: str) -> None:
    await session.execute(
        delete(AdminConfigDraft).where(AdminConfigDraft.environment == environment)
    )


async def _fetch_publish_events(
    session: AsyncSession, environment: str, limit: int
) -> list[AdminConfigPublishEvent]:
    result = await session.execute(
        select(AdminConfigPublishEvent)
        .where(AdminConfigPublishEvent.environment == environment)
        .order_by(AdminConfigPublishEvent.published_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _add_publish_event(session: AsyncSession, event: AdminConfigPublishEvent) -> None:
    session.add(event)


def _uuid_or_none(value: str) -> Any:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------- #
# Validation and audit                                                        #
# --------------------------------------------------------------------------- #
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
            400, "Value is empty. Send null to mark the saved value for removal."
        )
    return value.strip()


def _audit_rejected(
    ctx: AuditContext, *, environment: Optional[str], name: str, code: str
) -> None:
    """Record a refused request. No value of any kind is recorded."""
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


def _check_target(
    ctx: AuditContext,
    *,
    environment: str,
    name: str,
    confirm: Optional[str],
    reason: Optional[str],
) -> tuple[ConfigKey, str]:
    """Check the key, environment, confirmation and reason for a draft write."""
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
    return key, clean_reason


def _audit_draft(
    ctx: AuditContext,
    key: ConfigKey,
    environment: str,
    *,
    action: str,
    change: Optional[str],
    reason: Optional[str],
    outcome: str,
) -> None:
    """Audit a draft change. Key name and change type only, never a value."""
    audit(
        action,
        resource=AUDIT_RESOURCE,
        resource_id=f"{environment}:{key.name}",
        organization_id=PLATFORM_ORG,
        user_id=ctx.actor_id,
        meta={
            "admin_email": ctx.actor_email,
            "environment": environment,
            "key": key.name,
            "kind": key.kind,
            "change": change,
            "reason": reason,
            "outcome": outcome,
            "ip": ctx.ip,
            "request_id": ctx.request_id,
        },
    )


def _describe(
    key: ConfigKey, stored: Optional[str], environment: str
) -> dict[str, Any]:
    """Masked view of one value. Secrets show a tail; plain values only for local."""
    is_set = bool(stored)
    if key.kind == "secret":
        return {
            "is_set": is_set,
            "masked_tail": mask_secret(stored) if is_set else None,
            "value": None,
        }
    return {
        "is_set": is_set,
        "masked_tail": None,
        "value": stored if (is_set and environment == "local") else None,
    }


# --------------------------------------------------------------------------- #
# Read model                                                                  #
# --------------------------------------------------------------------------- #
async def _restart_pending(session: AsyncSession, runtime: str) -> bool:
    """True when this process runs an environment whose latest publish came after it started."""
    events = await _fetch_publish_events(session, runtime, 1)
    return bool(events) and events[0].published_at > config_overrides.PROCESS_STARTED_AT


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
    drafts = await _fetch_drafts(session, env)
    draft_names = {draft.name for draft in drafts}
    restart_required = await _restart_pending(session, runtime)

    items: list[dict[str, Any]] = []
    for key in REGISTRY:
        if env not in key.environments:
            continue
        row = rows.get(key.name)
        deployment_value = os.environ.get(key.name) if visible else None
        stored_value = _decrypt_value(row.value_encrypted) if row is not None else None

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
            "draft_pending": key.name in draft_names,
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
        "draft_count": len(drafts),
        "groups": list(GROUPS),
        "items": items,
    }


async def list_drafts(session: AsyncSession, *, environment: str) -> dict[str, Any]:
    """Pending drafts with a masked before and after for each key."""
    if environment not in ENVIRONMENTS:
        raise ConfigConsoleError(400, "Environment must be local or production.")
    runtime = current_environment()
    active = {row.name: row for row in await _fetch_rows(session, environment)}
    entries: list[dict[str, Any]] = []
    for draft in sorted(
        await _fetch_drafts(session, environment), key=lambda d: d.name
    ):
        key = BY_NAME.get(draft.name)
        if key is None:
            continue
        before_stored = (
            _decrypt_value(active[draft.name].value_encrypted)
            if draft.name in active
            else None
        )
        if draft.action == "set":
            after_stored = _decrypt_value(draft.value_encrypted)
            readable = after_stored is not None
        else:
            after_stored = None
            readable = True
        entries.append(
            {
                "name": key.name,
                "group": key.group,
                "kind": key.kind,
                "action": draft.action,
                "readable": readable,
                "changed": before_stored != after_stored,
                "before": _describe(key, before_stored, environment),
                "after": _describe(key, after_stored, environment),
                "updated_at": draft.updated_at.isoformat()
                if draft.updated_at
                else None,
            }
        )
    return {
        "environment": environment,
        "runtime_environment": runtime,
        "deployment_visible": environment == runtime,
        "publish_required": bool(entries),
        "drafts": entries,
    }


async def publish_history(
    session: AsyncSession, *, environment: str, limit: int = HISTORY_LIMIT
) -> dict[str, Any]:
    """The most recent publishes. Key names and change types only."""
    if environment not in ENVIRONMENTS:
        raise ConfigConsoleError(400, "Environment must be local or production.")
    events = await _fetch_publish_events(
        session, environment, min(limit, HISTORY_LIMIT)
    )
    return {
        "environment": environment,
        "items": [
            {
                "id": str(event.id),
                "published_at": event.published_at.isoformat(),
                "published_by_email": event.published_by_email,
                "reason": event.reason,
                "changes": list(event.changes or []),
            }
            for event in events
        ],
    }


# --------------------------------------------------------------------------- #
# Writes                                                                      #
# --------------------------------------------------------------------------- #
async def save_draft(
    session: AsyncSession,
    *,
    ctx: AuditContext,
    environment: str,
    name: str,
    value: Optional[str],
    confirm: Optional[str],
    reason: Optional[str],
) -> dict[str, Any]:
    """Save a draft for one key. ``value=None`` drafts a removal of the active value."""
    key, clean_reason = _check_target(
        ctx, environment=environment, name=name, confirm=confirm, reason=reason
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

    active = {row.name: row for row in await _fetch_rows(session, environment)}
    drafts = {draft.name: draft for draft in await _fetch_drafts(session, environment)}
    existing_draft = drafts.get(name)

    if clean_value is None:
        if name not in active:
            # Nothing is active, so there is nothing to remove. Drop a pending draft for it.
            if existing_draft is not None:
                await _delete_draft(session, environment=environment, name=name)
                await session.commit()
            _audit_draft(
                ctx,
                key,
                environment,
                action="draft_save",
                change="clear",
                reason=clean_reason,
                outcome="no_change",
            )
            await flush_pending(session)
            return {
                "name": name,
                "environment": environment,
                "status": "unchanged",
                "active": False,
                "publish_required": False,
                "restart_required": False,
            }
        action = "clear"
        encrypted: Optional[str] = None
    else:
        try:
            encrypted = encrypt(clean_value)
        except RuntimeError as exc:
            raise ConfigConsoleError(
                503, "The encryption key is not configured on this server."
            ) from exc
        action = "set"

    await _upsert_draft(
        session,
        existing=existing_draft,
        environment=environment,
        name=name,
        action=action,
        value_encrypted=encrypted,
        actor_id=ctx.actor_id,
        now=datetime.now(timezone.utc),
    )
    await session.commit()
    _audit_draft(
        ctx,
        key,
        environment,
        action="draft_save",
        change=action,
        reason=clean_reason,
        outcome="drafted",
    )
    await flush_pending(session)
    log.info(
        "config console: draft %s %s:%s by %s", action, environment, name, ctx.actor_id
    )
    return {
        "name": name,
        "environment": environment,
        "status": "draft_saved" if action == "set" else "draft_removal_saved",
        "active": False,
        "publish_required": True,
        "restart_required": False,
    }


async def discard_draft(
    session: AsyncSession, *, ctx: AuditContext, environment: str, name: str
) -> dict[str, Any]:
    """Delete one pending draft. The active value is not changed."""
    if environment not in ENVIRONMENTS:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=400,
            code="bad_environment",
            message="Environment must be local or production.",
        )
    key: Optional[ConfigKey] = BY_NAME.get(name)
    drafts = {draft.name for draft in await _fetch_drafts(session, environment)}
    if key is None or name not in drafts:
        raise _reject(
            ctx,
            environment=environment,
            name=name,
            status=404,
            code="no_draft",
            message="There is no draft for this key.",
        )
    await _delete_draft(session, environment=environment, name=name)
    await session.commit()
    _audit_draft(
        ctx,
        key,
        environment,
        action="draft_discard",
        change=None,
        reason=None,
        outcome="discarded",
    )
    await flush_pending(session)
    return {
        "name": name,
        "environment": environment,
        "status": "discarded",
        "active": False,
        "restart_required": False,
    }


async def publish_drafts(
    session: AsyncSession,
    *,
    ctx: AuditContext,
    environment: str,
    confirm: Optional[str],
    reason: Optional[str],
    reviewed: list[str],
) -> dict[str, Any]:
    """Copy every draft for one environment into the active store, in one transaction."""
    clean_reason = (reason or "").strip()

    def refuse(status: int, code: str, message: str) -> ConfigConsoleError:
        return _reject(
            ctx,
            environment=environment,
            name="publish",
            status=status,
            code=code,
            message=message,
        )

    if environment not in ENVIRONMENTS:
        raise refuse(400, "bad_environment", "Environment must be local or production.")
    if confirm != environment:
        raise refuse(
            400, "confirm_mismatch", f"Type {environment} in the confirm field."
        )
    if len(clean_reason) < MIN_REASON_LENGTH or len(clean_reason) > MAX_REASON_LENGTH:
        raise refuse(
            400,
            "reason_length",
            f"Give a reason of {MIN_REASON_LENGTH} to {MAX_REASON_LENGTH} characters.",
        )

    drafts = sorted(await _fetch_drafts(session, environment), key=lambda d: d.name)
    if not drafts:
        raise refuse(409, "no_drafts", "There are no draft changes to publish.")
    if sorted(set(reviewed)) != [draft.name for draft in drafts]:
        raise refuse(
            409,
            "drafts_changed",
            "The drafts changed since you reviewed them. Review the diff again before publishing.",
        )

    # Check every draft before writing anything. One bad draft stops the whole publish.
    for draft in drafts:
        key = BY_NAME.get(draft.name)
        if (
            key is None
            or not key.console_managed
            or environment not in key.environments
        ):
            raise refuse(
                400,
                "draft_not_applicable",
                "A draft is for a key that cannot be set here. Discard it, then publish again.",
            )
        if draft.action == "set" and _decrypt_value(draft.value_encrypted) is None:
            raise refuse(
                503,
                "draft_unreadable",
                "A draft cannot be read with the current encryption key. Discard it and save it again.",
            )

    active = {row.name: row for row in await _fetch_rows(session, environment)}
    now = datetime.now(timezone.utc)
    changes: list[dict[str, str]] = []
    for draft in drafts:
        if draft.action == "set":
            # The draft ciphertext is copied as it is, so the plaintext is not needed here.
            await _upsert_row(
                session,
                existing=active.get(draft.name),
                environment=environment,
                name=draft.name,
                value_encrypted=draft.value_encrypted or "",
                actor_id=ctx.actor_id,
                now=now,
            )
            changes.append({"name": draft.name, "change": "set"})
        else:
            if draft.name in active:
                await _delete_row(session, environment=environment, name=draft.name)
            changes.append({"name": draft.name, "change": "clear"})

    await _delete_drafts(session, environment=environment)
    _add_publish_event(
        session,
        AdminConfigPublishEvent(
            environment=environment,
            published_by=_uuid_or_none(ctx.actor_id),
            published_by_email=ctx.actor_email,
            published_at=now,
            reason=clean_reason,
            changes=changes,
        ),
    )
    await session.commit()

    names = [change["name"] for change in changes]
    audit(
        "publish",
        resource=AUDIT_RESOURCE,
        resource_id=f"{environment}:publish",
        organization_id=PLATFORM_ORG,
        user_id=ctx.actor_id,
        meta={
            "admin_email": ctx.actor_email,
            "environment": environment,
            "changes": [f"{c['name']}:{c['change']}" for c in changes],
            "changed_keys": names,
            "reason": clean_reason,
            "outcome": "published",
            "ip": ctx.ip,
            "request_id": ctx.request_id,
        },
    )
    await flush_pending(session)
    log.info(
        "config console: published %d change(s) to %s by %s",
        len(changes),
        environment,
        ctx.actor_id,
    )
    return {
        "environment": environment,
        "status": "published",
        "published_count": len(changes),
        "changed_keys": names,
        "active": True,
        "restart_required": True,
    }


async def reload_overrides(
    ctx: AuditContext, *, confirm: Optional[str], reason: Optional[str]
) -> dict[str, Any]:
    """Re-read active values into this process. Other workers keep their values until restart."""
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
