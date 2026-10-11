"""Agent prompt versioning service (features #7/#8).

Captures immutable snapshots of an agent's prompt + config each time a new
version is published, exposes the version history, computes structured /
unified diffs between any two versions (the prompt diff viewer), and
restores a prior version (one-click rollback).

All functions are organization-scoped — the caller passes the request's
``organization_id`` and we only ever touch rows for that tenant.
"""
from __future__ import annotations

import difflib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent
from app.database.models.agent_config import AgentConfig
from app.database.models.agent_prompt_version import AgentPromptVersion


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.astimezone(timezone.utc).isoformat() if dt else None


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


async def _get_agent(
    session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID
) -> Optional[Agent]:
    return await session.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.organization_id == org_id)
        .where(Agent.deleted_at.is_(None))
    )


async def _get_config(
    session: AsyncSession, agent_id: uuid.UUID
) -> Optional[AgentConfig]:
    return await session.scalar(
        select(AgentConfig).where(AgentConfig.agent_id == agent_id)
    )


def _version_payload(v: AgentPromptVersion) -> dict[str, Any]:
    return {
        "id": str(v.id),
        "version": v.version,
        "label": v.label,
        "note": v.note,
        "system_prompt": v.system_prompt,
        "temperature": _num(v.temperature),
        "max_tokens": v.max_tokens,
        "voice": v.voice,
        "language": v.language,
        "greeting": v.greeting,
        "config": v.config or {},
        "is_current": v.is_current,
        "created_by": str(v.created_by) if v.created_by else None,
        "created_at": _iso(v.created_at),
    }


def _config_snapshot(cfg: Optional[AgentConfig], agent: Agent) -> dict[str, Any]:
    """Materialize the current editable state into a flat dict."""
    if cfg is None:
        return {
            "system_prompt": None,
            "temperature": 0.70,
            "max_tokens": 1024,
            "voice": None,
            "language": "en-US",
            "greeting": None,
            "config": {},
        }
    return {
        "system_prompt": cfg.system_prompt,
        "temperature": _num(cfg.temperature),
        "max_tokens": cfg.max_tokens,
        "voice": cfg.voice,
        "language": cfg.language,
        "greeting": cfg.greeting,
        "config": cfg.config or {},
    }


async def list_versions(
    session: AsyncSession, org_id: uuid.UUID, agent_id: uuid.UUID
) -> dict[str, Any]:
    agent = await _get_agent(session, org_id, agent_id)
    if agent is None:
        return {"found": False, "agent_id": str(agent_id), "versions": []}

    rows = (
        await session.scalars(
            select(AgentPromptVersion)
            .where(AgentPromptVersion.agent_id == agent_id)
            .where(AgentPromptVersion.organization_id == org_id)
            .order_by(AgentPromptVersion.version.desc())
        )
    ).all()

    cfg = await _get_config(session, agent_id)
    return {
        "found": True,
        "agent_id": str(agent_id),
        "agent_name": agent.name,
        "current": _config_snapshot(cfg, agent),
        "count": len(rows),
        "versions": [_version_payload(v) for v in rows],
    }


async def publish_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    *,
    label: Optional[str] = None,
    note: Optional[str] = None,
) -> dict[str, Any]:
    """Freeze the agent's current config as a new immutable version."""
    agent = await _get_agent(session, org_id, agent_id)
    if agent is None:
        return {"found": False}

    cfg = await _get_config(session, agent_id)
    snap = _config_snapshot(cfg, agent)

    next_version = (
        await session.scalar(
            select(func.coalesce(func.max(AgentPromptVersion.version), 0)).where(
                AgentPromptVersion.agent_id == agent_id
            )
        )
    ) + 1

    # Demote any previous "current" snapshot.
    await session.execute(
        update(AgentPromptVersion)
        .where(AgentPromptVersion.agent_id == agent_id)
        .where(AgentPromptVersion.is_current.is_(True))
        .values(is_current=False)
    )

    row = AgentPromptVersion(
        agent_id=agent_id,
        organization_id=org_id,
        version=next_version,
        label=label or f"Version {next_version}",
        note=note,
        system_prompt=snap["system_prompt"],
        temperature=snap["temperature"],
        max_tokens=snap["max_tokens"],
        voice=snap["voice"],
        language=snap["language"],
        greeting=snap["greeting"],
        config=snap["config"],
        is_current=True,
        created_by=user_id,
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return {"found": True, "version": _version_payload(row)}


def _line_diff(old: Optional[str], new: Optional[str]) -> dict[str, Any]:
    old_lines = (old or "").splitlines()
    new_lines = (new or "").splitlines()
    unified = list(
        difflib.unified_diff(
            old_lines, new_lines, fromfile="previous", tofile="selected", lineterm=""
        )
    )
    added = removed = 0
    hunks: list[dict[str, str]] = []
    for line in unified:
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("@@"):
            hunks.append({"type": "hunk", "text": line})
        elif line.startswith("+"):
            added += 1
            hunks.append({"type": "add", "text": line[1:]})
        elif line.startswith("-"):
            removed += 1
            hunks.append({"type": "remove", "text": line[1:]})
        else:
            hunks.append({"type": "context", "text": line[1:] if line.startswith(" ") else line})
    similarity = round(
        difflib.SequenceMatcher(None, old or "", new or "").ratio() * 100, 1
    )
    return {
        "added": added,
        "removed": removed,
        "similarity": similarity,
        "changed": (old or "") != (new or ""),
        "lines": hunks,
    }


def _field_changes(a: dict[str, Any], b: dict[str, Any]) -> list[dict[str, Any]]:
    fields = [
        ("temperature", "Temperature"),
        ("max_tokens", "Max tokens"),
        ("voice", "Voice"),
        ("language", "Language"),
        ("greeting", "Greeting"),
    ]
    changes: list[dict[str, Any]] = []
    for key, label in fields:
        if a.get(key) != b.get(key):
            changes.append({"field": label, "from": a.get(key), "to": b.get(key)})
    return changes


async def _resolve_side(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent: Agent,
    version: Optional[int],
) -> Optional[dict[str, Any]]:
    """``version=None`` (or 0) means the live/current config."""
    if not version:
        cfg = await _get_config(session, agent.id)
        snap = _config_snapshot(cfg, agent)
        snap.update({"version": 0, "label": "Current (unpublished)"})
        return snap
    row = await session.scalar(
        select(AgentPromptVersion)
        .where(AgentPromptVersion.agent_id == agent.id)
        .where(AgentPromptVersion.organization_id == org_id)
        .where(AgentPromptVersion.version == version)
    )
    if row is None:
        return None
    payload = _version_payload(row)
    payload["label"] = row.label or f"Version {row.version}"
    return payload


async def diff_versions(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    from_version: Optional[int],
    to_version: Optional[int],
) -> dict[str, Any]:
    agent = await _get_agent(session, org_id, agent_id)
    if agent is None:
        return {"found": False}

    left = await _resolve_side(session, org_id, agent, from_version)
    right = await _resolve_side(session, org_id, agent, to_version)
    if left is None or right is None:
        return {"found": False, "reason": "version_not_found"}

    return {
        "found": True,
        "agent_id": str(agent_id),
        "agent_name": agent.name,
        "from": {"version": left.get("version"), "label": left.get("label")},
        "to": {"version": right.get("version"), "label": right.get("label")},
        "prompt_diff": _line_diff(left.get("system_prompt"), right.get("system_prompt")),
        "field_changes": _field_changes(left, right),
    }


async def restore_version(
    session: AsyncSession,
    org_id: uuid.UUID,
    agent_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    version: int,
) -> dict[str, Any]:
    """Copy a prior version's snapshot back into the live agent config and
    record the restore as a new current version."""
    agent = await _get_agent(session, org_id, agent_id)
    if agent is None:
        return {"found": False}

    src = await session.scalar(
        select(AgentPromptVersion)
        .where(AgentPromptVersion.agent_id == agent_id)
        .where(AgentPromptVersion.organization_id == org_id)
        .where(AgentPromptVersion.version == version)
    )
    if src is None:
        return {"found": False, "reason": "version_not_found"}

    cfg = await _get_config(session, agent_id)
    if cfg is None:
        cfg = AgentConfig(agent_id=agent_id)
        session.add(cfg)

    cfg.system_prompt = src.system_prompt
    if src.temperature is not None:
        cfg.temperature = src.temperature
    if src.max_tokens is not None:
        cfg.max_tokens = src.max_tokens
    cfg.voice = src.voice
    if src.language:
        cfg.language = src.language
    cfg.greeting = src.greeting
    cfg.config = src.config or {}
    await session.flush()

    published = await publish_version(
        session,
        org_id,
        agent_id,
        user_id,
        label=f"Restore of v{version}",
        note=f"Rolled back to version {version}.",
    )
    return {
        "found": True,
        "restored_from": version,
        "version": published.get("version"),
    }
