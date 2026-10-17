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

import hmac
import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent_channel import AgentChannel
from app.database.session import get_db
from app.services import omnichannel_service
from app.services.channels import adapters as channel_adapters
from app.services.channels import binding_secrets
from app.services.channels.config import get_channels_config

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
    # SDK messages arrive tagged mobile/desktop, but the binding is the "sdk" channel row.
    binding_channel = "sdk" if parsed.provider == "sdk" else parsed.channel
    base = (
        select(AgentChannel)
        .where(AgentChannel.channel == binding_channel)
        .where(AgentChannel.enabled.is_(True))
    )
    if parsed.provider == "twilio" and parsed.to_address:
        # Match the business number this message was sent to.
        num = parsed.to_address
        return await db.scalar(
            base.where(AgentChannel.phone_number.in_([num, f"+{num}", num.lstrip("+")]))
        )
    if parsed.provider == "meta" and parsed.to_address:
        # Match the WhatsApp Cloud API phone number id this message arrived on.
        return await db.scalar(
            base.where(
                AgentChannel.configuration["phone_number_id"].astext
                == parsed.to_address
            )
        )
    if parsed.provider == "meta_instagram" and parsed.to_address:
        # Match the Instagram account id (recipient of the DM) this message arrived on.
        return await db.scalar(
            base.where(
                AgentChannel.configuration["instagram_account_id"].astext
                == parsed.to_address
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


EMAIL_SECRET_HEADER = "x-email-inbound-secret"
TELEGRAM_SECRET_HEADER = "x-telegram-bot-api-secret-token"
SDK_SIGNATURE_HEADER = "x-oraone-signature"


def _header_secret_matches(expected: str | None, presented: str | None) -> bool:
    """Constant-time equality; a missing secret or header never matches (fail closed)."""
    if not expected or not presented:
        return False
    return hmac.compare_digest(expected.encode("utf-8"), presented.encode("utf-8"))


def _email_request_is_authentic(request: Request) -> bool:
    cfg = get_channels_config()
    return _header_secret_matches(
        cfg.email_inbound_secret, request.headers.get(EMAIL_SECRET_HEADER)
    )


def _binding_request_is_authentic(
    provider: str, binding: AgentChannel, request: Request, raw_body: bytes
) -> bool:
    """Per-binding authentication for providers whose webhook is not signed upstream.

    Twilio and Meta are verified before parsing; email uses a deployment-wide secret.
    Telegram and the SDK carry a secret per binding, so it is checked here once the
    binding is known.
    """
    if provider == "telegram":
        return _header_secret_matches(
            binding_secrets.read_secret(
                binding.configuration, "telegram_webhook_secret"
            ),
            request.headers.get(TELEGRAM_SECRET_HEADER),
        )
    if provider == "sdk":
        return channel_adapters.verify_sdk_signature(
            binding_secrets.read_secret(binding.configuration, "sdk_secret"),
            raw_body,
            request.headers.get(SDK_SIGNATURE_HEADER),
        )
    return True


async def _process(
    provider: str,
    request: Request,
    db: AsyncSession,
    *,
    route_token: str | None = None,
):
    adapter = channel_adapters.get_adapter(provider)
    if adapter is None:
        return {"ok": False, "error": "unsupported provider"}, None, None

    # Only the SDK signs the raw body. Read it before any form parsing: after request.form()
    # Starlette no longer exposes the raw bytes (Twilio's path has already parsed the form).
    raw_body = await request.body() if provider == "sdk" else b""
    form, body_json = await _read_payload(request)
    parsed = adapter.parse(
        form=form,
        json=body_json,
        headers=dict(request.headers),
        params=dict(request.query_params),
    )
    if parsed is not None and route_token:
        # The Telegram bot token comes from the webhook path, never from the query string.
        parsed.bot_token = route_token
    if parsed is None or not (parsed.text or "").strip():
        return {"ok": True, "skipped": "no message"}, None, None

    binding = await _resolve_binding(db, parsed)
    if binding is None:
        log.info("no agent bound for %s/%s", provider, parsed.channel)
        return {"ok": True, "skipped": "no agent bound"}, None, None

    if not _binding_request_is_authentic(provider, binding, request, raw_body):
        log.warning("inbound rejected: bad or missing secret provider=%s", provider)
        return Response(status_code=401), None, None

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
        provider_message_id=parsed.provider_message_id,
        meta=parsed.meta,
    )
    reply = await omnichannel_service.handle_inbound(db, msg)
    await db.commit()
    return None, (adapter, binding, parsed), reply


@router.post("/telegram/{token}/inbound")
async def telegram_inbound(
    token: str, request: Request, db: AsyncSession = Depends(get_db)
):
    # The path token selects the binding; the X-Telegram-Bot-Api-Secret-Token header
    # authenticates the request against that binding's telegram_webhook_secret.
    early, ctx, reply = await _process("telegram", request, db, route_token=token)
    if early is not None:
        return early
    adapter, binding, parsed = ctx
    if reply.handled and reply.text:
        await adapter.send(binding=binding, parsed=parsed, text=reply.text)
    return {"ok": True}


@router.get("/meta/inbound")
async def meta_webhook_handshake(request: Request):
    """Meta's one-time webhook verification: echo ``hub.challenge`` when the token matches."""
    cfg = get_channels_config()
    params = request.query_params
    expected = cfg.meta_whatsapp_verify_token
    if (
        expected
        and params.get("hub.mode") == "subscribe"
        and hmac.compare_digest(params.get("hub.verify_token", ""), expected)
    ):
        return Response(
            content=params.get("hub.challenge", ""), media_type="text/plain"
        )
    return Response(status_code=403)


async def _handle_meta_inbound(provider: str, request: Request, db: AsyncSession):
    """Shared Meta POST path (WhatsApp and Instagram share one app secret)."""
    # Verify the signature over the raw body before anything is parsed or answered.
    raw = await request.body()
    cfg = get_channels_config()
    if not channel_adapters.verify_meta_signature(
        cfg.meta_whatsapp_app_secret, raw, request.headers.get("x-hub-signature-256")
    ):
        return Response(status_code=401)
    early, ctx, reply = await _process(provider, request, db)
    if early is not None:
        return early
    adapter, binding, parsed = ctx
    if reply.handled and reply.text:
        await adapter.send(binding=binding, parsed=parsed, text=reply.text)
    return {"ok": True}


@router.post("/meta/inbound")
async def meta_inbound(request: Request, db: AsyncSession = Depends(get_db)):
    return await _handle_meta_inbound("meta", request, db)


@router.get("/meta_instagram/inbound")
async def meta_instagram_handshake(request: Request):
    """Instagram webhook verification. Meta uses one verify token per app, so this reuses it."""
    return await meta_webhook_handshake(request)


@router.post("/meta_instagram/inbound")
async def meta_instagram_inbound(request: Request, db: AsyncSession = Depends(get_db)):
    # Declared before the generic /{provider}/inbound route so this signed path always wins.
    return await _handle_meta_inbound("meta_instagram", request, db)


async def _twilio_request_is_signed(request: Request) -> bool:
    """Twilio signs the public URL plus form fields with the account auth token."""
    cfg = get_channels_config()
    if not cfg.twilio_auth_token or not cfg.public_api_base_url:
        # Fail closed: without both settings the request cannot be verified.
        return False
    form = dict((await request.form()).items())
    url = cfg.public_api_base_url + request.url.path
    if request.url.query:
        url += "?" + request.url.query
    return channel_adapters.verify_twilio_signature(
        cfg.twilio_auth_token, url, form, request.headers.get("x-twilio-signature")
    )


@router.post("/{provider}/inbound")
async def channel_inbound(
    provider: str, request: Request, db: AsyncSession = Depends(get_db)
):
    if provider == "telegram":
        # Telegram is served only at /telegram/{token}/inbound, never with a query token.
        return Response(status_code=404)
    if provider == "twilio" and not await _twilio_request_is_signed(request):
        return Response(status_code=401)
    if provider == "email" and not _email_request_is_authentic(request):
        return Response(status_code=401)
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
            "conversation_id": str(reply.conversation_id)
            if reply.conversation_id
            else None,
            "grounded": reply.grounded,
            "confidence": reply.confidence,
            "generated": bool(getattr(reply, "generated", False)),
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
