"""Outbound calling API: campaigns, per-lead attempts, and Twilio's status callback.

``router`` (prefix ``/api/calls``) is for signed-in users and is scoped to the
caller's organization and active project, like the leads routes.

``callback_router`` (prefix ``/api/voice``) receives Twilio status callbacks. It
has no user session, so it must verify ``X-Twilio-Signature`` and fails closed.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Permission
from app.database.models.call_campaign import AttemptStatus, CallAttempt, CallCampaign
from app.database.models.lead import LeadStatus, LeadTemperature
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.calls import AttemptRead, CampaignCounts, CampaignCreate, CampaignRead
from app.services import audit as audit_module
from app.services.authorization import require_permission
from app.services.calls import campaign_service
from app.services.calls.campaign_service import CampaignError
from app.services.channels import adapters
from app.services.channels.config import get_channels_config

router = APIRouter(prefix="/api/calls", tags=["calls"])
callback_router = APIRouter(prefix="/api/voice", tags=["calls"])
log = logging.getLogger("app.calls")


# ─────────────────────────── helpers ───────────────────────────


def _http(error: CampaignError) -> HTTPException:
    return HTTPException(error.status_code, error.message)


def _parse_lead_filter(
    lead_status: Optional[str], lead_temperature: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    status_value = None
    if lead_status:
        status_value = lead_status.strip().lower()
        if status_value not in {s.value for s in LeadStatus}:
            raise HTTPException(422, f"Invalid lead_status {lead_status!r}.")
    temperature_value = None
    if lead_temperature:
        temperature_value = lead_temperature.strip().lower()
        if temperature_value not in {t.value for t in LeadTemperature}:
            raise HTTPException(422, f"Invalid lead_temperature {lead_temperature!r}.")
    return status_value, temperature_value


def _to_read(campaign: CallCampaign, counts: dict[str, int]) -> CampaignRead:
    return CampaignRead(
        id=campaign.id,
        project_id=campaign.project_id,
        name=campaign.name,
        status=campaign.status,
        timezone=campaign.timezone,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        counts=CampaignCounts(**counts),
    )


async def _load_campaign(
    session: AsyncSession, *, campaign_id: uuid.UUID, pctx: ProjectContext
) -> CallCampaign:
    campaign = await session.scalar(
        select(CallCampaign)
        .where(CallCampaign.id == campaign_id)
        .where(CallCampaign.organization_id == pctx.organization_id)
        .where(CallCampaign.project_id == pctx.project_id)
    )
    if campaign is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campaign not found.")
    return campaign


async def _read_with_counts(
    session: AsyncSession, campaign: CallCampaign
) -> CampaignRead:
    counts = (await campaign_service.campaign_counts(session, [campaign.id]))[
        campaign.id
    ]
    return _to_read(campaign, counts)


# ─────────────────────────── campaigns ───────────────────────────


@router.post(
    "/campaigns",
    response_model=CampaignRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a calling campaign and plan its attempts",
)
async def create_campaign(
    payload: CampaignCreate,
    _: OrgContext = Depends(require_permission(Permission.CALLS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignRead:
    lead_status, lead_temperature = _parse_lead_filter(
        payload.lead_status, payload.lead_temperature
    )
    leads = await campaign_service.select_leads(
        session,
        organization_id=pctx.organization_id,
        project_id=pctx.project_id,
        lead_ids=payload.lead_ids,
        lead_status=lead_status,
        lead_temperature=lead_temperature,
    )
    try:
        campaign = await campaign_service.create_campaign(
            session,
            organization_id=pctx.organization_id,
            project_id=pctx.project_id,
            created_by=pctx.user_id,
            name=payload.name.strip(),
            timezone_name=payload.timezone.strip(),
            leads=leads,
        )
    except CampaignError as e:
        raise _http(e) from e
    counts = (await campaign_service.campaign_counts(session, [campaign.id]))[
        campaign.id
    ]
    audit_module.audit(
        "create",
        resource="call_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign.id),
        meta={"queued": counts["queued"], "skipped": counts["skipped"]},
    )
    await session.commit()
    await session.refresh(campaign)
    return _to_read(campaign, counts)


@router.get(
    "/campaigns", response_model=list[CampaignRead], summary="List calling campaigns"
)
async def list_campaigns(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: OrgContext = Depends(require_permission(Permission.CALLS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[CampaignRead]:
    campaigns = (
        await session.scalars(
            select(CallCampaign)
            .where(CallCampaign.organization_id == pctx.organization_id)
            .where(CallCampaign.project_id == pctx.project_id)
            .order_by(desc(CallCampaign.created_at), CallCampaign.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    counts = await campaign_service.campaign_counts(session, [c.id for c in campaigns])
    return [_to_read(c, counts[c.id]) for c in campaigns]


@router.get(
    "/campaigns/{campaign_id}",
    response_model=CampaignRead,
    summary="Get a calling campaign",
)
async def get_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.CALLS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignRead:
    campaign = await _load_campaign(session, campaign_id=campaign_id, pctx=pctx)
    return await _read_with_counts(session, campaign)


@router.post(
    "/campaigns/{campaign_id}/start",
    response_model=CampaignRead,
    summary="Start a campaign: places the next call, then continues after each call ends",
)
async def start_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.CALLS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignRead:
    campaign = await _load_campaign(session, campaign_id=campaign_id, pctx=pctx)
    if not campaign_service.can_start(campaign.status):
        raise HTTPException(409, "Only a draft or paused campaign can be started.")
    try:
        campaign_service.require_calling_config()
    except CampaignError as e:
        raise _http(e) from e

    campaign.status = "running"
    audit_module.audit(
        "start",
        resource="call_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign.id),
    )
    await session.commit()
    try:
        await campaign_service.dial_next(session, campaign_id=campaign.id)
    except CampaignError as e:
        raise _http(e) from e
    await session.refresh(campaign)
    return await _read_with_counts(session, campaign)


@router.post(
    "/campaigns/{campaign_id}/pause",
    response_model=CampaignRead,
    summary="Pause a campaign. A call already in progress finishes; no new call is placed",
)
async def pause_campaign(
    campaign_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.CALLS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> CampaignRead:
    campaign = await _load_campaign(session, campaign_id=campaign_id, pctx=pctx)
    if not campaign_service.can_pause(campaign.status):
        raise HTTPException(409, "Only a running campaign can be paused.")
    campaign.status = "paused"
    audit_module.audit(
        "pause",
        resource="call_campaign",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        resource_id=str(campaign.id),
    )
    await session.commit()
    await session.refresh(campaign)
    return await _read_with_counts(session, campaign)


@router.get(
    "/campaigns/{campaign_id}/attempts",
    response_model=list[AttemptRead],
    summary="List the attempts of a campaign, including skipped leads and reasons",
)
async def list_attempts(
    campaign_id: uuid.UUID,
    status_: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: OrgContext = Depends(require_permission(Permission.CALLS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[AttemptRead]:
    await _load_campaign(session, campaign_id=campaign_id, pctx=pctx)
    stmt = (
        select(CallAttempt)
        .where(CallAttempt.organization_id == pctx.organization_id)
        .where(CallAttempt.campaign_id == campaign_id)
    )
    if status_:
        value = status_.strip().lower()
        if value not in AttemptStatus.ALL:
            raise HTTPException(422, f"Invalid status {status_!r}.")
        stmt = stmt.where(CallAttempt.status == value)
    rows = (
        await session.scalars(
            stmt.order_by(CallAttempt.created_at, CallAttempt.id)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [AttemptRead.model_validate(r) for r in rows]


# ─────────────────────────── Twilio status callback ───────────────────────────


@callback_router.post(
    "/status",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Twilio Voice status callback (signature required)",
)
async def twilio_voice_status(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> Response:
    cfg = get_channels_config()
    if not cfg.twilio_auth_token or not cfg.public_api_base_url:
        # Fail closed: without the token and the public URL the signature cannot be checked.
        log.warning("call_status_rejected reason=not_configured")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized.")

    form = dict(await request.form())
    url = cfg.public_api_base_url + request.url.path
    if not adapters.verify_twilio_signature(
        cfg.twilio_auth_token, url, form, request.headers.get("x-twilio-signature")
    ):
        log.warning("call_status_rejected reason=bad_signature")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unauthorized.")

    call_sid = str(form.get("CallSid") or "")
    call_status = str(form.get("CallStatus") or "")
    if not call_sid or not call_status:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "CallSid and CallStatus are required."
        )

    transition = await campaign_service.record_call_status(
        session,
        call_sid=call_sid,
        call_status=call_status,
        duration=str(form.get("CallDuration") or "") or None,
    )
    await session.commit()

    if transition is not None:
        # The call ended: place the next one, if the campaign is still running.
        try:
            await campaign_service.dial_next(
                session, campaign_id=transition.campaign_id
            )
        except Exception as e:  # noqa: BLE001 - the callback must still succeed
            await session.rollback()
            log.warning(
                "call_queue_advance_failed campaign=%s error=%s",
                transition.campaign_id,
                type(e).__name__,
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
