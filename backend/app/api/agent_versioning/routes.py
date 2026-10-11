"""Agent prompt-versioning endpoints (features #7/#8).

Org-scoped + audit-logged. Lets users publish immutable snapshots of an
agent's prompt/config, browse the version history, diff any two versions
(prompt diff viewer) and roll back to a prior version.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import agent_versioning as av
from app.services.audit import audit

router = APIRouter(prefix="/api/agents", tags=["agent-versioning"])


class PublishRequest(BaseModel):
    label: Optional[str] = Field(default=None, max_length=160)
    note: Optional[str] = Field(default=None, max_length=2000)


class RestoreRequest(BaseModel):
    version: int = Field(..., ge=1)


@router.get("/{agent_id}/versions", summary="List an agent's prompt versions")
async def list_versions(
    agent_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await av.list_versions(session, ctx.organization_id, agent_id)
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Agent not found")
    return data


@router.post("/{agent_id}/versions", summary="Publish a new prompt version")
async def publish_version(
    agent_id: uuid.UUID,
    payload: PublishRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await av.publish_version(
        session, ctx.organization_id, agent_id, ctx.user_id,
        label=payload.label, note=payload.note,
    )
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Agent not found")
    await session.commit()
    audit("create", resource="agent_prompt_version",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          resource_id=str(agent_id),
          meta={"version": data.get("version", {}).get("version")})
    return data


@router.get("/{agent_id}/versions/diff", summary="Diff two prompt versions")
async def diff_versions(
    agent_id: uuid.UUID,
    from_version: Optional[int] = Query(None, ge=0, description="0/omit = current"),
    to_version: Optional[int] = Query(None, ge=0, description="0/omit = current"),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await av.diff_versions(
        session, ctx.organization_id, agent_id, from_version, to_version
    )
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Agent or version not found")
    return data


@router.post("/{agent_id}/versions/restore", summary="Roll back to a prior version")
async def restore_version(
    agent_id: uuid.UUID,
    payload: RestoreRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> dict:
    data = await av.restore_version(
        session, ctx.organization_id, agent_id, ctx.user_id, payload.version
    )
    if not data.get("found"):
        raise HTTPException(status_code=404, detail="Agent or version not found")
    await session.commit()
    audit("update", resource="agent_prompt_version",
          organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
          resource_id=str(agent_id),
          meta={"restored_from": data.get("restored_from")})
    return data
