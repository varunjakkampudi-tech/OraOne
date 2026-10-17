"""Marketing campaigns API: email, SMS and WhatsApp sends to a chosen lead list.

Every endpoint is organization- and project-scoped through ``ProjectContext``. Reads need
``leads.read`` (viewers have it); creating, sending and cancelling need ``leads.write``.
The unsubscribe endpoints are public and authorised only by their signed token.
"""

from __future__ import annotations

import html
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.marketing import MarketingCampaign
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.marketing import (
    CampaignCreate,
    CampaignDetail,
    CampaignRead,
    RecipientRead,
)
from app.services.audit import audit
from app.services.authorization import require_permission
from app.services.channels.config import get_channels_config
from app.services.marketing import campaigns as campaign_service
from app.services.marketing.campaigns import (
    SEND_BATCH_SIZE,
    CampaignConflict,
    CampaignError,
    CampaignNotFound,
)
from app.services.marketing.unsubscribe import (
    InvalidUnsubscribeToken,
    apply_unsubscribe,
)
from app.services.workflow_engine import ensure_default_senders, get_outbound_sender

router = APIRouter(prefix="/api/marketing", tags=["marketing"])
log = logging.getLogger("app.marketing")


# ─────────────────────────── helpers ───────────────────────────


def _http(exc: CampaignError) -> HTTPException:
    if isinstance(exc, CampaignNotFound):
        return HTTPException(status.HTTP_404_NOT_FOUND, str(exc))
    if isinstance(exc, CampaignConflict):
        return HTTPException(status.HTTP_409_CONFLICT, str(exc))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


def _lead_label(name: Optional[str], email: Optional[str], phone: Optional[str]) -> str:
    return (
        (name or "").strip()
        or (email or "").strip()
        or (phone or "").strip()
        or "Unnamed lead"
    )


def _campaign_read(campaign: MarketingCampaign) -> CampaignRead:
    return CampaignRead.model_validate(campaign, from_attributes=True)


def _detail(campaign: MarketingCampaign, rows: list) -> CampaignDetail:
    recipients = [
        RecipientRead(
            id=recipient.id,
            lead_id=recipient.lead_id,
            lead_label=_lead_label(name, email, phone),
            status=recipient.status,
            skip_reason=recipient.skip_reason,
            failure_reason=recipient.failure_reason,
            sent_at=recipient.sent_at,
        )
        for recipient, name, email, phone in rows
    ]
    queued = sum(1 for r in recipients if r.status == "queued")
    return CampaignDetail(
        **_campaign_read(campaign).model_dump(),
        queued_count=queued,
        recipients=recipients,
    )


async def _load_detail(
    session: AsyncSession, pctx: ProjectContext, campaign_id: uuid.UUID
) -> CampaignDetail:
    try:
        campaign, rows = await campaign_service.get_campaign_with_recipients(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            campaign_id=campaign_id,
        )
    except CampaignError as exc:
        raise _http(exc) from exc
    return _detail(campaign, rows)


def _sender_for(channel: str):
    """The sender registry's sender for this channel. Refuses before any state changes."""
    ensure_default_senders()
    sender = get_outbound_sender(channel)
    if sender is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Messages cannot be sent on the {channel} channel yet.",
        )
    return sender


# ─────────────────────────── campaigns ───────────────────────────


@router.post(
    "/campaigns",
    response_model=CampaignDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a campaign and plan its recipients",
)
async def create_campaign(
    payload: CampaignCreate,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    try:
        campaign = await campaign_service.create_campaign(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            created_by=pctx.user_id,
            name=payload.name,
            channel=payload.channel.strip().lower(),
            subject=payload.subject,
            body=payload.body,
            lead_ids=payload.lead_ids,
        )
    except CampaignError as exc:
        raise _http(exc) from exc
    audit(
        "create",
        resource="marketing_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign.id),
        meta={"channel": campaign.channel, "skipped": campaign.skipped_count},
    )
    await session.commit()
    return await _load_detail(session, pctx, campaign.id)


@router.get("/campaigns", response_model=list[CampaignRead], summary="List campaigns")
async def list_campaigns(
    limit: int = Query(default=100, ge=1, le=200),
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[CampaignRead]:
    rows = await campaign_service.list_campaigns(
        session,
        organization_id=pctx.organization_id,
        project_id=pctx.project_id,
        limit=limit,
    )
    return [_campaign_read(row) for row in rows]


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignDetail,
    summary="Get a campaign with recipients",
)
async def get_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    return await _load_detail(session, pctx, campaign_id)


@router.post(
    "/campaigns/{campaign_id}/send",
    response_model=CampaignDetail,
    summary="Send a campaign in batches",
)
async def send_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    try:
        current = await campaign_service.get_campaign(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            campaign_id=campaign_id,
        )
    except CampaignError as exc:
        raise _http(exc) from exc
    sender = _sender_for(current.channel)

    try:
        await campaign_service.begin_send(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            campaign_id=campaign_id,
        )
    except CampaignError as exc:
        raise _http(exc) from exc
    await session.commit()  # the sending claim is visible before any provider call

    base_url = get_channels_config().public_api_base_url
    while True:
        handled = await campaign_service.send_next_batch(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            campaign_id=campaign_id,
            sender=sender,
            unsubscribe_base_url=base_url,
            batch_size=SEND_BATCH_SIZE,
        )
        await session.commit()
        if handled == 0:
            break

    await campaign_service.complete_campaign(
        session,
        organization_id=pctx.organization_id,
        project_id=pctx.project_id,
        campaign_id=campaign_id,
    )
    audit(
        "send",
        resource="marketing_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign_id),
        meta={"channel": current.channel},
    )
    await session.commit()
    return await _load_detail(session, pctx, campaign_id)


@router.post(
    "/campaigns/{campaign_id}/cancel",
    response_model=CampaignDetail,
    summary="Cancel a draft or scheduled campaign",
)
async def cancel_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignDetail:
    try:
        await campaign_service.cancel_campaign(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            campaign_id=campaign_id,
        )
    except CampaignError as exc:
        raise _http(exc) from exc
    audit(
        "cancel",
        resource="marketing_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign_id),
    )
    await session.commit()
    return await _load_detail(session, pctx, campaign_id)


# ─────────────────────────── unsubscribe (public) ───────────────────────────

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:32rem;margin:4rem auto;padding:0 1rem;color:#111}}
button{{font:inherit;padding:.6rem 1rem;border-radius:.5rem;border:1px solid #111;background:#111;color:#fff;cursor:pointer}}
</style></head><body><main>{body}</main></body></html>"""


def _page(title: str, body: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        _PAGE.format(title=html.escape(title), body=body),
        status_code=status_code,
        headers={
            "Cache-Control": "no-store",
            "Referrer-Policy": "no-referrer",
            "X-Robots-Tag": "noindex",
        },
    )


@router.get(
    "/unsubscribe",
    response_class=HTMLResponse,
    summary="Confirm unsubscribe from email marketing",
)
async def unsubscribe_form(
    token: str = Query(default="", max_length=1024),
) -> HTMLResponse:
    # A GET only shows the confirmation form. Mail scanners that prefetch links cannot unsubscribe anyone.
    safe_token = html.escape(token, quote=True)
    body = (
        "<h1>Unsubscribe from marketing emails</h1>"
        "<p>Confirm below and you will no longer receive marketing emails from this sender.</p>"
        f'<form method="post" action="/api/marketing/unsubscribe">'
        f'<input type="hidden" name="token" value="{safe_token}">'
        '<button type="submit">Confirm unsubscribe</button></form>'
    )
    return _page("Unsubscribe", body)


@router.post(
    "/unsubscribe",
    response_class=HTMLResponse,
    summary="Unsubscribe from email marketing",
)
async def unsubscribe(
    token: str = Form(default="", max_length=1024),
    session: AsyncSession = Depends(get_db),
) -> HTMLResponse:
    try:
        await apply_unsubscribe(session, token)
    except InvalidUnsubscribeToken as exc:
        await session.rollback()
        return _page(
            "Unsubscribe",
            f"<h1>We could not unsubscribe you</h1><p>{html.escape(str(exc))}</p>",
            status_code=400,
        )
    await session.commit()
    return _page(
        "Unsubscribed",
        "<h1>You are unsubscribed</h1><p>You will not receive more marketing emails from this sender.</p>",
    )
