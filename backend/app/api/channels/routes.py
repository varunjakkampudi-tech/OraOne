"""Channels & Deploy API — the Universal Agent's delivery surfaces.

One agent, every channel. These endpoints let the dashboard:

* list & toggle channels (Website Chat, Widget, WhatsApp, API, Webhooks, Forms),
* fetch everything needed to deploy (embed / npm / SDK / install guides /
  triggers), manage the domain allow-list, publish, and verify a live install.

All routes are organization-scoped and reuse the existing AgentChannel /
Widget / widget_service infrastructure — no AI logic is duplicated here.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models.agent import Agent
from app.database.models.widget import WidgetStatus
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.channels import (
    ChannelRead,
    ChannelsResponse,
    ChannelUpdate,
    DeployInfo,
    DomainsResponse,
    DomainsUpdate,
    PublishRequest,
    Verification,
)
from app.services import channels_service
from app.services.audit import audit


router = APIRouter(prefix="/api/agents", tags=["channels"])


async def _load_agent(session: AsyncSession, *, agent_id: uuid.UUID, organization_id: uuid.UUID) -> Agent:
    agent = await session.scalar(
        select(Agent)
        .where(Agent.id == agent_id)
        .where(Agent.organization_id == organization_id)
        .where(Agent.deleted_at.is_(None))
        .options(selectinload(Agent.config))
    )
    if agent is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def _channel_read(row, defn: dict) -> ChannelRead:
    return ChannelRead(
        channel=row.channel,
        label=defn["label"],
        description=defn["description"],
        icon=defn["icon"],
        enabled=bool(row.enabled),
        status=row.status,
        embeddable=bool(defn["embeddable"]),
        phone_number=row.phone_number,
        provider=row.provider,
        configuration=row.configuration or {},
    )


# ─────────────────────────── channels ───────────────────────────

@router.get("/{agent_id}/channels", response_model=ChannelsResponse)
async def list_channels(
    agent_id: uuid.UUID,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    rows = await channels_service.ensure_channels(session, agent)
    await session.commit()
    by_key = {d["channel"]: d for d in channels_service.CHANNEL_DEFS}
    items = [_channel_read(r, by_key[r.channel]) for r in rows if r.channel in by_key]
    return ChannelsResponse(agent_id=agent.id, agent_name=agent.name, items=items)


@router.patch("/{agent_id}/channels/{channel}", response_model=ChannelRead)
async def update_channel(
    agent_id: uuid.UUID,
    channel: str,
    payload: ChannelUpdate,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    if not channels_service.is_valid_channel(channel):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown channel")
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    row = await channels_service.update_channel(
        session,
        agent,
        channel,
        enabled=payload.enabled,
        status=payload.status,
        phone_number=payload.phone_number,
        provider=payload.provider,
        configuration=payload.configuration,
    )
    audit(
        "channel.update",
        resource="agent_channel",
        organization_id=str(org.organization_id),
        user_id=str(org.user_id),
        resource_id=str(agent.id),
        meta={"channel": channel, "enabled": row.enabled, "status": row.status},
    )
    await session.commit()
    defn = next(d for d in channels_service.CHANNEL_DEFS if d["channel"] == channel)
    return _channel_read(row, defn)


# ─────────────────────────── deploy ───────────────────────────

@router.get("/{agent_id}/deploy", response_model=DeployInfo)
async def get_deploy(
    agent_id: uuid.UUID,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    info = await channels_service.build_deploy_info(session, agent)
    await session.commit()
    return DeployInfo(**info)


@router.put("/{agent_id}/deploy/domains", response_model=DomainsResponse)
async def update_domains(
    agent_id: uuid.UUID,
    payload: DomainsUpdate,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    widget = await channels_service.ensure_widget(session, agent)
    domains = await channels_service.set_domains(session, widget, payload.domains)
    audit(
        "deploy.domains.update",
        resource="widget",
        organization_id=str(org.organization_id),
        user_id=str(org.user_id),
        resource_id=str(widget.id),
        meta={"domains": domains},
    )
    await session.commit()
    return DomainsResponse(domains=domains)


@router.post("/{agent_id}/deploy/publish", response_model=DeployInfo)
async def publish_deploy(
    agent_id: uuid.UUID,
    payload: PublishRequest,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    widget = await channels_service.ensure_widget(session, agent)
    if payload.publish:
        widget.status = WidgetStatus.published
        widget.published_at = channels_service.now_utc()
        # Make sure the embeddable channels are on when going live.
        await channels_service.update_channel(session, agent, "widget", enabled=True)
    else:
        widget.status = WidgetStatus.paused
    audit(
        "deploy.publish" if payload.publish else "deploy.pause",
        resource="widget",
        organization_id=str(org.organization_id),
        user_id=str(org.user_id),
        resource_id=str(widget.id),
        meta={"status": widget.status},
    )
    await session.flush()
    info = await channels_service.build_deploy_info(session, agent)
    await session.commit()
    return DeployInfo(**info)


@router.post("/{agent_id}/deploy/verify", response_model=Verification)
async def verify_deploy(
    agent_id: uuid.UUID,
    org: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    agent = await _load_agent(session, agent_id=agent_id, organization_id=org.organization_id)
    widget = await channels_service.ensure_widget(session, agent)
    result = await channels_service.verify_installation(session, widget)
    await session.commit()
    return Verification(**result)
