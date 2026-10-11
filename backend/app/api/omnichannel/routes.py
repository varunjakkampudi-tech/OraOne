"""Omnichannel inbound webhooks (Phase M).

A single set of provider webhooks that funnel every messaging channel
(WhatsApp, SMS, Telegram, Email, Mobile/Desktop SDK, …) into the ONE shared
:func:`omnichannel_service.handle_inbound` pipeline — same agent, same RAG,
same cross-channel memory as the website chat widget.

Routing: an adapter normalises the webhook, then we resolve the
:class:`AgentChannel` binding (by phone number / bot token / inbound address /
agent id) to learn which agent owns the surface, run the pipeline, and let the
adapter deliver the reply.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent_channel import AgentChannel
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters as channel_adapters

router = APIRouter(prefix="/api/channels", tags=["omnichannel"])
log = logging.getLogger("app.omnichannel.routes")


async def _read_payload(request: Request) -> tuple[dict, dict | None]:
    """Return (form, json) — whichever the provider sent."""
    ctype = (request.headers.get("content-type") or "").lower()
    form: dict = {}
    body_json: dict | None = None
    if "application/json" in ctype:
        try:
            body_json = await request.json()
        except Exception:  # noqa: BLE001
            body_json = None
    else:
        try:
            form = dict((await request.form()).items())
        except Exception:  # noqa: BLE001
            form = {}
        if not form:
            # Some providers send JSON without the header.
            try:
                body_json = await request.json()
            except Exception:  # noqa: BLE001
                body_json = None
    return form, body_json


async def _resolve_binding(
    db: AsyncSession, parsed: channel_adapters.ParsedInbound
) -> AgentChannel | None:
    """Find the AgentChannel that owns this inbound surface."""
    base = (
        select(AgentChannel)
        .where(AgentChannel.channel == parsed.channel)
        .where(AgentChannel.enabled.is_(True))
    )
    if parsed.provider == "twilio" and parsed.to_address:
        # Match the business number this message was sent to.
        num = parsed.to_address
        return await db.scalar(
            base.where(
                AgentChannel.phone_number.in_([num, f"+{num}", num.lstrip("+")])
            )
        )
    if parsed.provider == "telegram" and parsed.bot_token:
        return await db.scalar(
            base.where(
                AgentChannel.configuration["bot_token"].astext == parsed.bot_token
            )
        )
    if parsed.provider == "email" and parsed.to_address:
        return await db.scalar(
            base.where(
                AgentChannel.configuration["inbound_address"].astext
                == parsed.to_address
            )
        )
    if parsed.provider == "sdk" and parsed.route_value:
        try:
            import uuid

            return await db.scalar(
                base.where(AgentChannel.agent_id == uuid.UUID(parsed.route_value))
            )
        except (ValueError, TypeError):
            return None
    return None


async def _process(provider: str, request: Request, db: AsyncSession):
    adapter = channel_adapters.get_adapter(provider)
    if adapter is None:
        return {"ok": False, "error": "unsupported provider"}, None, None

    form, body_json = await _read_payload(request)
    parsed = adapter.parse(
        form=form,
        json=body_json,
        headers=dict(request.headers),
        params=dict(request.query_params),
    )
    if parsed is None or not (parsed.text or "").strip():
        return {"ok": True, "skipped": "no message"}, None, None

    binding = await _resolve_binding(db, parsed)
    if binding is None:
        log.info("no agent bound for %s/%s", provider, parsed.channel)
        return {"ok": True, "skipped": "no agent bound"}, None, None

    msg = omnichannel_service.InboundMessage(
        channel=parsed.channel,
        organization_id=binding.organization_id,
        agent_id=binding.agent_id,
        project_id=binding.project_id,
        text=parsed.text,
        name=parsed.name,
        phone=parsed.phone,
        email=parsed.email,
        handle=parsed.handle,
        external_id=parsed.external_id,
        external_thread_id=parsed.external_thread_id,
        meta=parsed.meta,
    )
    reply = await omnichannel_service.handle_inbound(db, msg)
    await db.commit()
    return None, (adapter, binding, parsed), reply


@router.post("/telegram/{token}/inbound")
async def telegram_inbound(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    early, ctx, reply = await _process("telegram", request, db)
    if early is not None:
        return early
    adapter, binding, parsed = ctx
    if reply.handled and reply.text:
        await adapter.send(binding=binding, parsed=parsed, text=reply.text)
    return {"ok": True}


@router.post("/{provider}/inbound")
async def channel_inbound(provider: str, request: Request, db: AsyncSession = Depends(get_db)):
    early, ctx, reply = await _process(provider, request, db)
    if early is not None:
        # SDK clients expect a JSON reply even on skip.
        return early
    adapter, binding, parsed = ctx

    # The native SDK is synchronous — return the reply in the HTTP response.
    if provider == "sdk":
        return {
            "ok": True,
            "reply": reply.text,
            "conversation_id": str(reply.conversation_id) if reply.conversation_id else None,
            "grounded": reply.grounded,
            "confidence": reply.confidence,
        }

    if reply.handled and reply.text:
        await adapter.send(binding=binding, parsed=parsed, text=reply.text)

    # Twilio messaging expects a 2xx (empty TwiML is fine — we already replied
    # via the REST API inside adapter.send).
    if provider == "twilio":
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml",
        )
    return {"ok": True}


@router.get("/providers")
async def list_providers():
    """Discovery: which inbound providers this deployment can receive."""
    return {"providers": channel_adapters.supported_providers()}
