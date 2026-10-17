"""Leads (CRM) API — capture, list, score and manage sales leads.

All endpoints are organization- + project-scoped (via ``ProjectContext``),
soft-delete aware and audit-logged. Leads are produced automatically by the
widget lead-capture endpoint and can also be created/edited manually here.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import asc, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.permissions import Permission
from app.database.models.lead import Lead, LeadStatus, LeadTemperature
from app.database.models.conversation import Conversation
from app.database.models.message import Message, MessageSender
from app.database.session import get_db
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext, get_current_project
from app.services.authorization import require_permission
from app.schemas.leads import (
    STATUS_LABELS,
    LeadImportColumn,
    LeadImportCommit,
    LeadImportPreview,
    LeadImportRow,
    LeadConversationMessage,
    LeadConversationRead,
    LeadCreate,
    LeadRead,
    LeadStats,
    LeadUpdate,
)
from app.services import lead_import_service, lead_service
from app.services.audit import audit
from app.services.lead_import_service import LeadImportError


router = APIRouter(prefix="/api/leads", tags=["leads"])
log = logging.getLogger("app.leads")


# ─────────────────────────── helpers ───────────────────────────


def _parse_status(value: Optional[str]) -> Optional[LeadStatus]:
    if value is None:
        return None
    try:
        return LeadStatus(value.strip().lower())
    except ValueError as e:
        valid = ", ".join(m.value for m in LeadStatus)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid status {value!r}. Allowed: {valid}.",
        ) from e


def _parse_temperature(value: Optional[str]) -> Optional[LeadTemperature]:
    if value is None:
        return None
    try:
        return LeadTemperature(value.strip().lower())
    except ValueError as e:
        valid = ", ".join(m.value for m in LeadTemperature)
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Invalid temperature {value!r}. Allowed: {valid}.",
        ) from e


def _consent_fields(extra: dict) -> dict:
    """Read-only consent provenance from ``extra``. Other extra keys are not exposed."""
    out: dict = {}
    for key in ("consent", "consent_source", "consent_note"):
        value = extra.get(key)
        if isinstance(value, str) and value.strip():
            out[key] = value.strip()
    recorded = extra.get("consent_recorded_at")
    if isinstance(recorded, str):
        try:
            out["consent_recorded_at"] = datetime.fromisoformat(recorded)
        except ValueError:
            pass
    return out


def _to_read(lead: Lead) -> LeadRead:
    extra = lead.extra or {}
    raw_tags = extra.get("tags")
    tags = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else []
    return LeadRead(
        **_consent_fields(extra),
        id=lead.id,
        organization_id=lead.organization_id,
        project_id=lead.project_id,
        conversation_id=lead.conversation_id,
        agent_id=lead.agent_id,
        widget_id=lead.widget_id,
        assigned_to=lead.assigned_to,
        name=lead.name,
        email=lead.email,
        phone=lead.phone,
        company=lead.company,
        intent=lead.intent,
        message=lead.message,
        source=lead.source,
        status=STATUS_LABELS.get(lead.status.value, lead.status.value.capitalize()),
        temperature=lead.temperature.value,
        score=lead.score,
        notes=extra.get("notes") or None,
        tags=tags,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


async def _load(
    session: AsyncSession, *, lead_id: uuid.UUID, organization_id: uuid.UUID
) -> Lead:
    lead = await session.scalar(
        select(Lead)
        .where(Lead.id == lead_id)
        .where(Lead.organization_id == organization_id)
        .where(Lead.deleted_at.is_(None))
    )
    if lead is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found.")
    return lead


# ─────────────────────────── routes ────────────────────────────


@router.get("", response_model=list[LeadRead], summary="List leads")
async def list_leads(
    q: Optional[str] = Query(default=None, max_length=200),
    status_: Optional[str] = Query(default=None, alias="status"),
    temperature: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort: str = Query(
        default="-created_at",
        pattern="^-?(created_at|updated_at|score|name)$",
    ),
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> list[LeadRead]:
    filters = [
        Lead.organization_id == pctx.organization_id,
        Lead.project_id == pctx.project_id,
        Lead.deleted_at.is_(None),
    ]
    if status_:
        filters.append(Lead.status == _parse_status(status_))
    if temperature:
        filters.append(Lead.temperature == _parse_temperature(temperature))
    if q:
        like = f"%{q.strip()}%"
        filters.append(
            or_(
                Lead.name.ilike(like),
                Lead.email.ilike(like),
                Lead.company.ilike(like),
                Lead.phone.ilike(like),
            )
        )

    sort_field = sort.lstrip("-")
    sort_dir = desc if sort.startswith("-") else asc
    col = {
        "created_at": Lead.created_at,
        "updated_at": Lead.updated_at,
        "score": Lead.score,
        "name": Lead.name,
    }[sort_field]

    rows = (
        await session.scalars(
            select(Lead)
            .where(*filters)
            .order_by(sort_dir(col))
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return [_to_read(r) for r in rows]


@router.get("/stats", response_model=LeadStats, summary="Lead pipeline KPIs")
async def lead_stats(
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadStats:
    base = [
        Lead.organization_id == pctx.organization_id,
        Lead.project_id == pctx.project_id,
        Lead.deleted_at.is_(None),
    ]

    by_status = dict(
        (
            await session.execute(
                select(Lead.status, func.count(Lead.id))
                .where(*base)
                .group_by(Lead.status)
            )
        ).all()
    )
    by_temp = dict(
        (
            await session.execute(
                select(Lead.temperature, func.count(Lead.id))
                .where(*base)
                .group_by(Lead.temperature)
            )
        ).all()
    )

    def s(key: LeadStatus) -> int:
        return int(by_status.get(key, 0))

    def t(key: LeadTemperature) -> int:
        return int(by_temp.get(key, 0))

    total = sum(int(v) for v in by_status.values())
    won = s(LeadStatus.won)
    qualified = s(LeadStatus.qualified)
    conversion = round((won / total) * 100, 1) if total else 0.0

    return LeadStats(
        total=total,
        new=s(LeadStatus.new),
        contacted=s(LeadStatus.contacted),
        qualified=qualified,
        won=won,
        lost=s(LeadStatus.lost),
        hot=t(LeadTemperature.hot),
        warm=t(LeadTemperature.warm),
        cold=t(LeadTemperature.cold),
        conversion_rate=conversion,
        appointments=won + qualified,
    )


@router.post(
    "",
    response_model=LeadRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a lead",
)
async def create_lead(
    payload: LeadCreate,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadRead:
    lead = await lead_service.create_lead(
        session,
        organization_id=pctx.organization_id,
        project_id=pctx.project_id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        intent=payload.intent,
        message=payload.message,
        source=payload.source or "manual",
        status=_parse_status(payload.status),
        score=payload.score,
        temperature=_parse_temperature(payload.temperature),
    )
    audit(
        "create",
        resource="lead",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        meta={"lead_id": str(lead.id), "source": lead.source},
    )
    await session.commit()
    await session.refresh(lead)
    return _to_read(lead)


@router.get("/{lead_id}", response_model=LeadRead, summary="Get a lead")
async def get_lead(
    lead_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadRead:
    lead = await _load(session, lead_id=lead_id, organization_id=pctx.organization_id)
    return _to_read(lead)


@router.get(
    "/{lead_id}/conversation",
    response_model=LeadConversationRead,
    summary="Get the chat thread that produced this lead",
)
async def lead_conversation(
    lead_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_READ)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadConversationRead:
    """Full transcript of the conversation a lead came from, so the whole
    exchange is visible right inside the CRM — even for anonymous visitors."""
    lead = await _load(session, lead_id=lead_id, organization_id=pctx.organization_id)
    if lead.conversation_id is None:
        return LeadConversationRead()

    conv = await session.get(Conversation, lead.conversation_id)
    if conv is None or conv.organization_id != pctx.organization_id:
        return LeadConversationRead()

    rows = (
        await session.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
            .limit(500)
        )
    ).all()
    messages = [
        LeadConversationMessage(
            role="assistant" if m.sender == MessageSender.agent else "user",
            content=m.message or "",
            created_at=m.created_at,
        )
        for m in rows
        if m.sender in (MessageSender.agent, MessageSender.customer)
    ]
    return LeadConversationRead(
        conversation_id=conv.id,
        channel=conv.channel.value if conv.channel else None,
        status=conv.status.value if conv.status else None,
        started_at=conv.started_at,
        messages=messages,
    )


@router.patch("/{lead_id}", response_model=LeadRead, summary="Update a lead")
async def update_lead(
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadRead:
    lead = await _load(session, lead_id=lead_id, organization_id=pctx.organization_id)

    if payload.name is not None:
        lead.name = payload.name or None
    if payload.email is not None:
        lead.email = payload.email or None
    if payload.phone is not None:
        lead.phone = payload.phone or None
    if payload.company is not None:
        lead.company = payload.company or None
    if payload.intent is not None:
        lead.intent = payload.intent or None
    if payload.status is not None:
        lead.status = _parse_status(payload.status)
    if payload.temperature is not None:
        lead.temperature = _parse_temperature(payload.temperature)
    if payload.score is not None:
        lead.score = payload.score
    if payload.assigned_to is not None:
        lead.assigned_to = payload.assigned_to
    if payload.notes is not None or payload.tags is not None:
        # JSONB needs a fresh dict for SQLAlchemy to detect the change.
        extra = dict(lead.extra or {})
        if payload.notes is not None:
            note = payload.notes.strip()
            if note:
                extra["notes"] = note
            else:
                extra.pop("notes", None)
        if payload.tags is not None:
            cleaned = []
            for t in payload.tags:
                t = (t or "").strip()[:40]
                if t and t not in cleaned:
                    cleaned.append(t)
            extra["tags"] = cleaned
        lead.extra = extra

    audit(
        "update",
        resource="lead",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        meta={"lead_id": str(lead.id)},
    )
    await session.commit()
    await session.refresh(lead)
    return _to_read(lead)


@router.delete(
    "/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a lead",
)
async def delete_lead(
    lead_id: uuid.UUID,
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> Response:
    lead = await _load(session, lead_id=lead_id, organization_id=pctx.organization_id)
    lead.deleted_at = func.now()
    audit(
        "delete",
        resource="lead",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        meta={"lead_id": str(lead.id)},
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────── contact import ───────────────────────────
#
# Two-step import. ``preview`` parses and validates the upload and reports
# per-row status without writing. ``commit`` repeats the same analysis on the
# re-uploaded file and saves only the valid rows. Duplicates are checked across
# the whole organization, not just the active project. Logs carry counts and
# ids only, never contact details.


async def _analyse_upload(
    file: UploadFile,
    session: AsyncSession,
    pctx: ProjectContext,
) -> lead_import_service.ParsedImport:
    try:
        data = await lead_import_service.read_upload(file)
        parsed = await run_in_threadpool(
            lead_import_service.prepare_import, data, file.filename or ""
        )
    except LeadImportError as e:
        raise HTTPException(e.status_code, e.message) from e
    await lead_import_service.classify_rows(
        session, organization_id=pctx.organization_id, parsed=parsed
    )
    return parsed


@router.post(
    "/import/preview",
    response_model=LeadImportPreview,
    summary="Preview a contact import (nothing is saved)",
)
async def preview_lead_import(
    file: UploadFile = File(...),
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadImportPreview:
    parsed = await _analyse_upload(file, session, pctx)
    counts = lead_import_service.summarise(parsed)
    log.info(
        "lead_import_preview org=%s rows=%d valid=%d",
        pctx.organization_id,
        len(parsed.rows),
        counts[lead_import_service.ROW_VALID],
    )
    return LeadImportPreview(
        file_name=parsed.file_name,
        file_format=parsed.file_format,
        total_rows=len(parsed.rows),
        valid=counts[lead_import_service.ROW_VALID],
        duplicate_existing=counts[lead_import_service.ROW_DUPLICATE_EXISTING],
        duplicate_in_file=counts[lead_import_service.ROW_DUPLICATE_IN_FILE],
        invalid=counts[lead_import_service.ROW_INVALID],
        columns=[LeadImportColumn(column=c, field=f) for c, f in parsed.columns],
        warnings=parsed.warnings,
        rows=[
            LeadImportRow(
                row_number=r.row_number,
                status=r.status,
                reason=r.reason,
                name=r.name,
                phone=r.phone,
                email=r.email,
                company=r.company,
                consent=r.consent,
            )
            for r in parsed.rows
        ],
    )


@router.post(
    "/import/commit",
    response_model=LeadImportCommit,
    status_code=status.HTTP_201_CREATED,
    summary="Save the valid rows of a contact import",
)
async def commit_lead_import(
    file: UploadFile = File(...),
    _: OrgContext = Depends(require_permission(Permission.LEADS_WRITE)),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> LeadImportCommit:
    # Serialise imports per organization for the rest of this transaction. The duplicate
    # check and the insert then run as one unit, so two concurrent commits can't both
    # insert the same contact. The lock is released automatically at commit or rollback.
    lock_key = int.from_bytes(
        hashlib.sha256(f"lead-import:{pctx.organization_id}".encode()).digest()[:8],
        "big",
        signed=True,
    )
    await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
    parsed = await _analyse_upload(file, session, pctx)
    counts = lead_import_service.summarise(parsed)
    upload_id, saved = await lead_import_service.save_valid_rows(
        session,
        organization_id=pctx.organization_id,
        project_id=pctx.project_id,
        user_id=pctx.user_id,
        parsed=parsed,
    )
    audit(
        "import",
        resource="lead",
        organization_id=str(pctx.organization_id),
        user_id=str(pctx.user_id),
        meta={
            "upload_id": str(upload_id),
            "source": "import",
            "file_format": parsed.file_format,
            "saved": saved,
            "total_rows": len(parsed.rows),
        },
    )
    await session.commit()
    log.info(
        "lead_import_commit org=%s upload=%s saved=%d",
        pctx.organization_id,
        upload_id,
        saved,
    )
    return LeadImportCommit(
        upload_id=upload_id,
        total_rows=len(parsed.rows),
        saved=saved,
        skipped_duplicate_existing=counts[lead_import_service.ROW_DUPLICATE_EXISTING],
        skipped_duplicate_in_file=counts[lead_import_service.ROW_DUPLICATE_IN_FILE],
        skipped_invalid=counts[lead_import_service.ROW_INVALID],
    )
