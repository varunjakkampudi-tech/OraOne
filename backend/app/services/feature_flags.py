"""Beta feature flags.

Flags are defined in code, so every flag has a reviewed name, description and
default. Rollout comes from these layers, highest priority first:

  1. An organisation override saved by a super-admin.
  2. A beta-cohort override for the caller's email hash, saved by a super-admin.
  3. The code-level rollout lists (organisation IDs and email hashes).
  4. The default, which is off for every flag.

Email addresses are never stored or returned. A cohort member is identified by
``sha256("oraone:beta-cohort:v1:" + lowercased email)``. The hash is
deterministic across environments, so config lists remain portable. It is
pseudonymous, not secret: anyone who holds a candidate address can recompute it.

Resolved flags are cached per (email hash, organisation) for 60 seconds in this
process. Admin writes clear the cache here. Other worker processes pick up a
change within the TTL.
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.feature_flag_override import FeatureFlagOverride
from app.services.audit import audit

log = logging.getLogger("app.feature_flags")

CACHE_TTL_SECONDS = 60.0
SCOPE_ORGANIZATION = "organization"
SCOPE_COHORT_MEMBER = "cohort_member"
_EMAIL_HASH_DOMAIN = "oraone:beta-cohort:v1:"
_MAX_CACHE_ENTRIES = 10_000

# Monotonic clock, kept as a module attribute so tests can advance time.
_clock = time.monotonic


class FeatureFlagError(Exception):
    """Raised for unknown flags. Carries the HTTP status to return."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class FlagDefinition:
    key: str
    description: str
    default_enabled: bool = False
    # Code-level rollout lists: organisation UUID strings and email hashes.
    rollout_organization_ids: frozenset[str] = frozenset()
    rollout_email_hashes: frozenset[str] = frozenset()


FLAG_DEFINITIONS: tuple[FlagDefinition, ...] = (
    FlagDefinition(
        key="admin_analytics_console",
        description="Platform analytics console for operators (beta).",
    ),
    FlagDefinition(
        key="org_analytics_summary",
        description="Organisation summary for owners on the analytics page (beta).",
    ),
)

_BY_KEY: dict[str, FlagDefinition] = {f.key: f for f in FLAG_DEFINITIONS}


def get_definition(key: str) -> Optional[FlagDefinition]:
    return _BY_KEY.get(key)


def hash_email(email: str) -> str:
    normalized = email.strip().lower()
    return hashlib.sha256((_EMAIL_HASH_DOMAIN + normalized).encode("utf-8")).hexdigest()


def resolve_flag(
    definition: FlagDefinition,
    *,
    organization_id: Optional[str],
    email_hash: str,
    org_override: Optional[bool],
    member_override: Optional[bool],
) -> bool:
    """Pure precedence rule. Off unless an explicit layer turns the flag on."""
    if org_override is not None:
        return org_override
    if member_override is not None:
        return member_override
    if organization_id and organization_id in definition.rollout_organization_ids:
        return True
    if email_hash in definition.rollout_email_hashes:
        return True
    return definition.default_enabled


_cache: dict[tuple[str, Optional[str]], tuple[float, frozenset[str]]] = {}


def invalidate_cache() -> None:
    _cache.clear()


async def _load_overrides(
    session: AsyncSession, email_hash: str, organization_id: Optional[str]
) -> tuple[dict[str, bool], dict[str, bool]]:
    conditions = [
        (FeatureFlagOverride.scope == SCOPE_COHORT_MEMBER)
        & (FeatureFlagOverride.scope_value == email_hash)
    ]
    if organization_id:
        conditions.append(
            (FeatureFlagOverride.scope == SCOPE_ORGANIZATION)
            & (FeatureFlagOverride.scope_value == organization_id)
        )
    rows = (
        (await session.execute(select(FeatureFlagOverride).where(or_(*conditions))))
        .scalars()
        .all()
    )
    org_map: dict[str, bool] = {}
    member_map: dict[str, bool] = {}
    for row in rows:
        target = org_map if row.scope == SCOPE_ORGANIZATION else member_map
        target[row.flag_key] = bool(row.enabled)
    return org_map, member_map


async def enabled_flag_keys(
    session: AsyncSession,
    *,
    email: str,
    organization_id: Optional[uuid.UUID] = None,
) -> list[str]:
    """Return the sorted keys of flags on for this caller. Cached for 60 seconds."""
    email_hash = hash_email(email)
    org_key = str(organization_id) if organization_id else None
    cache_key = (email_hash, org_key)
    now = _clock()
    cached = _cache.get(cache_key)
    if cached is not None and now - cached[0] < CACHE_TTL_SECONDS:
        return sorted(cached[1])

    org_map, member_map = await _load_overrides(session, email_hash, org_key)
    enabled = frozenset(
        d.key
        for d in FLAG_DEFINITIONS
        if resolve_flag(
            d,
            organization_id=org_key,
            email_hash=email_hash,
            org_override=org_map.get(d.key),
            member_override=member_map.get(d.key),
        )
    )
    if len(_cache) >= _MAX_CACHE_ENTRIES:
        _cache.clear()
    _cache[cache_key] = (now, enabled)
    return sorted(enabled)


async def _find_override(
    session: AsyncSession, flag_key: str, scope: str, scope_value: str
) -> Optional[FeatureFlagOverride]:
    return await session.scalar(
        select(FeatureFlagOverride).where(
            FeatureFlagOverride.flag_key == flag_key,
            FeatureFlagOverride.scope == scope,
            FeatureFlagOverride.scope_value == scope_value,
        )
    )


async def _write_override(
    session: AsyncSession,
    *,
    flag_key: str,
    scope: str,
    scope_value: str,
    enabled: Optional[bool],
    actor_id: uuid.UUID,
) -> tuple[Optional[bool], Optional[bool]]:
    """Set or clear one override. Returns (previous, new) values."""
    if get_definition(flag_key) is None:
        raise FeatureFlagError(404, "Unknown feature flag.")
    existing = await _find_override(session, flag_key, scope, scope_value)
    previous = existing.enabled if existing is not None else None
    if enabled is None:
        if existing is not None:
            await session.delete(existing)
    elif existing is None:
        session.add(
            FeatureFlagOverride(
                flag_key=flag_key,
                scope=scope,
                scope_value=scope_value,
                enabled=enabled,
                updated_by=actor_id,
            )
        )
    else:
        existing.enabled = enabled
        existing.updated_by = actor_id
    await session.flush()
    invalidate_cache()
    return previous, enabled


async def set_organization_override(
    session: AsyncSession,
    *,
    flag_key: str,
    organization_id: uuid.UUID,
    enabled: Optional[bool],
    actor_id: uuid.UUID,
) -> dict:
    previous, new = await _write_override(
        session,
        flag_key=flag_key,
        scope=SCOPE_ORGANIZATION,
        scope_value=str(organization_id),
        enabled=enabled,
        actor_id=actor_id,
    )
    audit(
        "feature_flag.organization_override_set",
        resource="feature_flag",
        organization_id=str(organization_id),
        user_id=str(actor_id),
        resource_id=flag_key,
        before={"enabled": previous},
        after={"enabled": new},
        meta={"scope": SCOPE_ORGANIZATION},
    )
    return {"flag_key": flag_key, "scope": SCOPE_ORGANIZATION, "enabled": new}


async def set_cohort_member(
    session: AsyncSession,
    *,
    flag_key: str,
    email: str,
    enabled: Optional[bool],
    actor_id: uuid.UUID,
) -> dict:
    email_hash = hash_email(email)
    previous, new = await _write_override(
        session,
        flag_key=flag_key,
        scope=SCOPE_COHORT_MEMBER,
        scope_value=email_hash,
        enabled=enabled,
        actor_id=actor_id,
    )
    # The audit record carries the hash only, never the address.
    audit(
        "feature_flag.cohort_member_set",
        resource="feature_flag",
        organization_id="",
        user_id=str(actor_id),
        resource_id=flag_key,
        before={"enabled": previous},
        after={"enabled": new},
        meta={"scope": SCOPE_COHORT_MEMBER, "member_hash": email_hash},
    )
    return {"flag_key": flag_key, "scope": SCOPE_COHORT_MEMBER, "enabled": new}


async def admin_overview(session: AsyncSession) -> list[dict]:
    """Every flag with its code defaults and runtime overrides. Holds no emails."""
    rows = (await session.execute(select(FeatureFlagOverride))).scalars().all()
    out: list[dict] = []
    for definition in FLAG_DEFINITIONS:
        mine = [r for r in rows if r.flag_key == definition.key]
        org_rows = [r for r in mine if r.scope == SCOPE_ORGANIZATION]
        member_rows = [r for r in mine if r.scope == SCOPE_COHORT_MEMBER]
        out.append(
            {
                "key": definition.key,
                "description": definition.description,
                "default_enabled": definition.default_enabled,
                "code_rollout": {
                    "organization_count": len(definition.rollout_organization_ids),
                    "member_count": len(definition.rollout_email_hashes),
                },
                "organization_overrides": [
                    {"organization_id": r.scope_value, "enabled": bool(r.enabled)}
                    for r in sorted(org_rows, key=lambda r: r.scope_value)
                ],
                "cohort": {
                    "member_count": len(member_rows),
                    "enabled_count": sum(1 for r in member_rows if r.enabled),
                    "disabled_count": sum(1 for r in member_rows if not r.enabled),
                },
            }
        )
    return out
