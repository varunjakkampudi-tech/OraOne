"""Integrations Platform API (Phase 10).

OraOne as the central AI layer over business apps: connect external
providers (Google Drive, Gmail, Slack, Notion, GitHub, Jira, …), sync
their content into a Knowledge Base, and let chat answer from it.

Endpoints
---------
* ``GET    /api/integrations``                  — catalog + per-org status
* ``GET    /api/integrations/{id}``             — one connected integration
* ``POST   /api/integrations/connect``          — connect (OAuth or mock)
* ``GET    /api/integrations/oauth/callback``   — OAuth redirect target
* ``POST   /api/integrations/{id}/sync``        — trigger a sync (background)
* ``DELETE /api/integrations/{id}``             — disconnect + purge docs
* ``GET    /api/integrations/{id}/jobs``        — recent sync jobs
* ``GET    /api/integrations/{id}/logs``        — recent sync logs

Tenant-safe: every read/write is scoped to the caller's organization.
Secrets are encrypted at rest and never returned in responses.
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt as jose_jwt
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors import registry
from app.connectors.base import ConnectorError
from app.core import crypto
from app.database.models.document import Document
from app.database.models.document_chunk import DocumentChunk
from app.database.models.integration import (
    ConnectionType,
    Integration,
    IntegrationStatus,
)
from app.database.models.integration_document import (
    IntegrationDocStatus,
    IntegrationDocument,
)
from app.database.models.project import Project
from app.database.models.sync_job import SyncJob, SyncJobStatus, SyncTrigger
from app.database.models.sync_log import SyncLog
from app.database.session import get_db
from app.middleware.org_context import (
    OrgContext,
    get_current_organization,
    require_role,
)
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.integrations import (
    BrowseResponse,
    ConnectRequest,
    ConnectResponse,
    IntegrationAnalytics,
    IntegrationCatalogEntry,
    IntegrationCatalogResponse,
    IntegrationHealth,
    IntegrationRead,
    ProviderCatalogItem,
    SelectionPayload,
    SyncedItemRead,
    SyncedItemsResponse,
    SyncJobListResponse,
    SyncJobRead,
    SyncLogListResponse,
    SyncLogRead,
)
from app.services import oauth_service
from app.services.audit import audit
from app.services.sync_service import run_sync

log = logging.getLogger("app.integrations")

router = APIRouter(tags=["integrations"])


# ─────────────────── OAuth state (CSRF-safe org binding) ───────────────────
# The OAuth callback is unauthenticated (it's a browser redirect from the
# provider), so we cannot trust query params for the org. Instead we mint a
# short-lived signed token at connect-time that carries the org/user, and
# verify its signature in the callback.
_STATE_TTL_SECONDS = 600
_STATE_ALG = "HS256"


def _state_secret() -> str:
    secret = os.environ.get("SECRET_KEY") or os.environ.get("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "Cannot sign OAuth state: set SECRET_KEY or JWT_SECRET_KEY. "
            "Refusing to use an insecure hardcoded fallback."
        )
    return secret


def issue_oauth_state(*, provider: str, organization_id: uuid.UUID, user_id) -> str:
    now = int(time.time())
    claims = {
        "provider": provider,
        "org": str(organization_id),
        "sub": str(user_id),
        "iat": now,
        "exp": now + _STATE_TTL_SECONDS,
    }
    return jose_jwt.encode(claims, _state_secret(), algorithm=_STATE_ALG)


def verify_oauth_state(token: str) -> dict:
    return jose_jwt.decode(token, _state_secret(), algorithms=[_STATE_ALG])


def _frontend_url() -> str:
    return os.environ.get("FRONTEND_URL", "http://localhost:3000").rstrip("/")


# ─────────────────── helpers ───────────────────

def _catalog_item(spec) -> ProviderCatalogItem:
    return ProviderCatalogItem(
        provider=spec.provider,
        name=spec.name,
        category=spec.category,
        type=spec.type.value,
        auth=spec.auth,
        icon=spec.icon,
        color=spec.color,
        description=spec.description,
        available=spec.available,
    )


async def _integration_for_org(
    session: AsyncSession, *, integration_id: uuid.UUID, organization_id: uuid.UUID
) -> Optional[Integration]:
    return await session.scalar(
        select(Integration)
        .where(Integration.id == integration_id)
        .where(Integration.organization_id == organization_id)
        .where(Integration.deleted_at.is_(None))
    )


async def _by_provider(
    session: AsyncSession, *, provider: str, organization_id: uuid.UUID
) -> Optional[Integration]:
    return await session.scalar(
        select(Integration)
        .where(Integration.provider == provider)
        .where(Integration.organization_id == organization_id)
        .where(Integration.deleted_at.is_(None))
    )


# ─────────────────── catalog ───────────────────

@router.get(
    "/api/integrations",
    response_model=IntegrationCatalogResponse,
    summary="List the integration catalog with this org's connection status",
)
async def list_integrations(
    category: Optional[str] = Query(default=None),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> IntegrationCatalogResponse:
    ctx = pctx.org
    connected = {
        i.provider: i
        for i in (
            await session.scalars(
                select(Integration)
                .where(Integration.organization_id == ctx.organization_id)
                .where(Integration.project_id == pctx.project_id)
                .where(Integration.deleted_at.is_(None))
            )
        ).all()
    }

    items: list[IntegrationCatalogEntry] = []
    for spec in registry.list_specs():
        if category and spec.category != category:
            continue
        row = connected.get(spec.provider)
        items.append(
            IntegrationCatalogEntry(
                catalog=_catalog_item(spec),
                integration=(
                    IntegrationRead.model_validate(row.__dict__) if row else None
                ),
            )
        )
    return IntegrationCatalogResponse(items=items, total=len(items))


@router.get(
    "/api/integrations/{integration_id}",
    response_model=IntegrationRead,
    summary="Get one connected integration",
)
async def get_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> IntegrationRead:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    return IntegrationRead.model_validate(row.__dict__)


# ─────────────────── connect ───────────────────

@router.post(
    "/api/integrations/connect",
    response_model=ConnectResponse,
    summary="Connect a provider (OAuth or mock)",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def connect_integration(
    payload: ConnectRequest,
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> ConnectResponse:
    ctx = pctx.org
    spec = registry.get_spec(payload.provider)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown provider {payload.provider!r}.",
        )

    use_real = (
        not payload.mock
        and spec.available
        and oauth_service.is_configured(payload.provider)
    )

    # Real OAuth, first leg: hand back an authorize URL for the browser.
    if use_real and not payload.code:
        state = issue_oauth_state(
            provider=payload.provider,
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
        )
        try:
            url = oauth_service.build_authorize_url(payload.provider, state=state)
        except ConnectorError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        return ConnectResponse(authorize_url=url)

    # Resolve tokens — real exchange or mock.
    connection_type = ConnectionType.oauth if use_real else ConnectionType.mock
    try:
        if use_real:
            result = oauth_service.complete_connect(payload.provider, code=payload.code)
        else:
            connector = registry.get_connector_for_provider(payload.provider)
            result = connector.connect(code=payload.code)
    except ConnectorError as e:
        raise HTTPException(status_code=502, detail=f"Connection failed: {e}") from e

    row = await _by_provider(
        session, provider=payload.provider, organization_id=ctx.organization_id
    )
    if row is None:
        row = Integration(
            organization_id=ctx.organization_id,
            project_id=pctx.project_id,
            provider=spec.provider,
            category=spec.category,
            type=spec.type,
        )
        session.add(row)

    row.connection_type = connection_type
    row.status = IntegrationStatus.connected
    row.access_token = crypto.encrypt(result.access_token)
    row.refresh_token = crypto.encrypt(result.refresh_token)
    row.token_expires_at = result.token_expires_at
    row.external_account = result.external_account
    if payload.config:
        row.config = {**(row.config or {}), **payload.config}
    if result.config:
        row.config = {**(row.config or {}), **result.config}
    row.last_error = None

    await session.commit()
    await session.refresh(row)

    audit(
        "connect",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={
            "provider": row.provider,
            "connection_type": row.connection_type.value,
            "external_account": row.external_account,
        },
    )
    return ConnectResponse(integration=IntegrationRead.model_validate(row.__dict__))


@router.get(
    "/api/integrations/google/callback",
    summary="Google OAuth redirect target — completes the connection",
    include_in_schema=False,
)
async def google_oauth_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    """Browser redirect target for Google OAuth.

    Verifies the signed ``state`` (which binds the flow to an org/user),
    exchanges the authorization code for tokens, persists the connection
    with encrypted secrets, then bounces the browser back to the app.
    """
    base = f"{_frontend_url()}/app/integrations"

    if error:
        return RedirectResponse(f"{base}?error={error}", status_code=302)
    if not code or not state:
        return RedirectResponse(f"{base}?error=missing_code", status_code=302)

    try:
        claims = verify_oauth_state(state)
    except JWTError:
        return RedirectResponse(f"{base}?error=invalid_state", status_code=302)

    provider = claims.get("provider", "google_drive")
    try:
        organization_id = uuid.UUID(str(claims["org"]))
    except (KeyError, ValueError):
        return RedirectResponse(f"{base}?error=invalid_state", status_code=302)
    user_id = claims.get("sub", "system")

    spec = registry.get_spec(provider)
    if spec is None:
        return RedirectResponse(f"{base}?error=unknown_provider", status_code=302)

    try:
        result = oauth_service.complete_connect(provider, code=code)
    except ConnectorError as e:
        log.warning("google oauth token exchange failed: %s", e)
        return RedirectResponse(f"{base}?error=token_exchange_failed", status_code=302)

    row = await _by_provider(
        session, provider=provider, organization_id=organization_id
    )
    if row is None:
        default_project_id = await session.scalar(
            select(Project.id)
            .where(Project.organization_id == organization_id)
            .where(Project.deleted_at.is_(None))
            .where(Project.is_default.is_(True))
        )
        row = Integration(
            organization_id=organization_id,
            project_id=default_project_id,
            provider=spec.provider,
            category=spec.category,
            type=spec.type,
        )
        session.add(row)

    row.connection_type = ConnectionType.oauth
    row.status = IntegrationStatus.connected
    row.access_token = crypto.encrypt(result.access_token)
    row.refresh_token = crypto.encrypt(result.refresh_token)
    row.token_expires_at = result.token_expires_at
    row.external_account = result.external_account
    if result.config:
        row.config = {**(row.config or {}), **result.config}
    row.last_error = None

    await session.commit()
    await session.refresh(row)

    audit(
        "connect",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(organization_id),
        user_id=str(user_id),
        after={
            "provider": row.provider,
            "connection_type": row.connection_type.value,
            "external_account": row.external_account,
        },
    )
    return RedirectResponse(f"{base}?connected={provider}", status_code=302)


# ─────────────────── sync ───────────────────

@router.post(
    "/api/integrations/{integration_id}/sync",
    response_model=SyncJobRead,
    summary="Trigger a sync for an integration",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def trigger_sync(
    integration_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SyncJobRead:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    if row.status == IntegrationStatus.disconnected:
        raise HTTPException(status_code=409, detail="Integration is not connected.")

    job = SyncJob(
        integration_id=row.id,
        organization_id=ctx.organization_id,
        status=SyncJobStatus.queued,
        trigger=SyncTrigger.manual,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    background_tasks.add_task(
        run_sync, row.id, trigger=SyncTrigger.manual, job_id=job.id
    )
    audit(
        "sync_triggered",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"provider": row.provider, "job_id": str(job.id)},
    )
    return SyncJobRead.model_validate(job.__dict__)


# ─────────────────── browse & selection (selective sync) ───────────────────

@router.get(
    "/api/integrations/{integration_id}/browse",
    response_model=BrowseResponse,
    summary="Browse folders/files in the provider for the file-picker",
)
async def browse_integration(
    integration_id: uuid.UUID,
    parent: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    recent: bool = Query(default=False),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> BrowseResponse:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    if row.status == IntegrationStatus.disconnected:
        raise HTTPException(status_code=409, detail="Integration is not connected.")
    try:
        result = registry.get_connector(row).browse(
            parent_id=parent, query=q, recent=recent
        )
    except ConnectorError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return BrowseResponse(**result)


@router.get(
    "/api/integrations/{integration_id}/selection",
    response_model=SelectionPayload,
    summary="Get the current sync selection (scope) for an integration",
)
async def get_selection(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SelectionPayload:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    selection = (row.config or {}).get("selection")
    if not selection:
        return SelectionPayload()
    return SelectionPayload.model_validate(selection)


@router.put(
    "/api/integrations/{integration_id}/selection",
    response_model=SelectionPayload,
    summary="Set the sync selection (folders/files + filters)",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def set_selection(
    integration_id: uuid.UUID,
    payload: SelectionPayload,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SelectionPayload:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    # "Quick" mode = recent files only; encode as a recent_days window.
    if payload.mode == "quick" and not payload.options.recent_days:
        payload.options.recent_days = 30

    selection = payload.model_dump()
    row.config = {**(row.config or {}), "selection": selection}

    # Seed the manifest with the explicitly chosen folders/files so the
    # "Synced Items" UI shows them immediately (status=pending until synced).
    await _seed_manifest(session, row, payload, organization_id=ctx.organization_id)

    await session.commit()
    audit(
        "selection_updated",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={
            "provider": row.provider,
            "mode": payload.mode,
            "folders": len(payload.folders),
            "files": len(payload.files),
        },
    )
    return payload


@router.get(
    "/api/integrations/{integration_id}/items",
    response_model=SyncedItemsResponse,
    summary="List the resolved synced items (manifest) for an integration",
)
async def list_synced_items(
    integration_id: uuid.UUID,
    limit: int = Query(default=200, ge=1, le=1000),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SyncedItemsResponse:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    total = int(
        await session.scalar(
            select(func.count(IntegrationDocument.id)).where(
                IntegrationDocument.integration_id == row.id
            )
        )
        or 0
    )
    rows = (
        await session.scalars(
            select(IntegrationDocument)
            .where(IntegrationDocument.integration_id == row.id)
            .order_by(
                IntegrationDocument.is_folder.desc(),
                IntegrationDocument.name.asc(),
            )
            .limit(limit)
        )
    ).all()
    selection = (row.config or {}).get("selection")
    return SyncedItemsResponse(
        items=[SyncedItemRead.model_validate(r) for r in rows],
        total=total,
        selection=SelectionPayload.model_validate(selection) if selection else None,
    )


@router.post(
    "/api/integrations/{integration_id}/items/remove",
    status_code=status.HTTP_200_OK,
    summary="Deselect synced items and purge their KB documents",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def remove_synced_items(
    integration_id: uuid.UUID,
    payload: dict,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone

    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    external_ids = [str(x) for x in (payload.get("external_ids") or [])]
    if not external_ids:
        raise HTTPException(status_code=422, detail="external_ids is required.")

    manifest_rows = (
        await session.scalars(
            select(IntegrationDocument)
            .where(IntegrationDocument.integration_id == row.id)
            .where(IntegrationDocument.external_id.in_(external_ids))
        )
    ).all()

    removed = 0
    for item in manifest_rows:
        if item.document_id is not None:
            await session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.document_id == item.document_id
                )
            )
            doc = await session.get(Document, item.document_id)
            if doc is not None and doc.deleted_at is None:
                doc.deleted_at = datetime.now(timezone.utc)
                removed += 1
        item.selected = False
        item.status = IntegrationDocStatus.removed

    # Prune the deselected ids from the stored selection scope.
    selection = (row.config or {}).get("selection")
    if selection:
        drop = set(external_ids)
        for key in ("folders", "files"):
            kept = [
                ref
                for ref in (selection.get(key) or [])
                if (ref.get("external_id") if isinstance(ref, dict) else ref) not in drop
            ]
            selection[key] = kept
        row.config = {**(row.config or {}), "selection": selection}

    await session.commit()
    audit(
        "items_removed",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"provider": row.provider, "documents_removed": removed},
    )
    return {"detail": "Items removed.", "documents_removed": removed}


async def _seed_manifest(
    session: AsyncSession,
    integration: Integration,
    payload: SelectionPayload,
    *,
    organization_id: uuid.UUID,
) -> None:
    """Upsert manifest rows for the explicitly selected folders/files."""
    existing = {
        r.external_id: r
        for r in (
            await session.scalars(
                select(IntegrationDocument).where(
                    IntegrationDocument.integration_id == integration.id
                )
            )
        ).all()
    }
    chosen: set[str] = set()

    def _upsert(ref, *, is_folder: bool) -> None:
        chosen.add(ref.external_id)
        item = existing.get(ref.external_id)
        if item is None:
            session.add(
                IntegrationDocument(
                    integration_id=integration.id,
                    organization_id=organization_id,
                    external_id=ref.external_id,
                    name=ref.name or ref.external_id,
                    mime_type=ref.mime_type,
                    path=ref.path,
                    is_folder=is_folder,
                    selected=True,
                    status=IntegrationDocStatus.pending,
                )
            )
        else:
            item.selected = True
            item.is_folder = is_folder
            if ref.name:
                item.name = ref.name
            if ref.path:
                item.path = ref.path
            if item.status == IntegrationDocStatus.removed:
                item.status = IntegrationDocStatus.pending

    for folder in payload.folders:
        _upsert(folder, is_folder=True)
    for f in payload.files:
        _upsert(f, is_folder=False)

    # Deselect manifest rows that the user removed from the explicit scope
    # (resolved child files are reconciled later by the sync run).
    for ext_id, item in existing.items():
        if item.external_id not in chosen and item.external_id in {
            *(fr.external_id for fr in payload.folders),
            *(fl.external_id for fl in payload.files),
        }:
            item.selected = False


# ─────────────────── disconnect ───────────────────

@router.delete(
    "/api/integrations/{integration_id}",
    status_code=status.HTTP_200_OK,
    summary="Disconnect an integration and remove its synced documents",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def disconnect_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    # Best-effort provider-side token revocation.
    try:
        registry.get_connector(row).disconnect()
    except ConnectorError:
        pass

    # Purge synced documents + their chunks from the Knowledge Base.
    docs = (
        await session.scalars(
            select(Document)
            .where(Document.integration_id == row.id)
            .where(Document.deleted_at.is_(None))
        )
    ).all()
    from datetime import datetime, timezone

    removed = 0
    for doc in docs:
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        doc.deleted_at = datetime.now(timezone.utc)
        removed += 1

    row.status = IntegrationStatus.disconnected
    row.access_token = None
    row.refresh_token = None
    row.token_expires_at = None
    row.external_account = None
    row.last_error = None
    await session.commit()

    audit(
        "disconnect",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"provider": row.provider, "documents_removed": removed},
    )
    return {"detail": "Integration disconnected.", "documents_removed": removed}


# ─────────────────── jobs & logs ───────────────────

@router.get(
    "/api/integrations/{integration_id}/jobs",
    response_model=SyncJobListResponse,
    summary="Recent sync jobs for an integration",
)
async def list_jobs(
    integration_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SyncJobListResponse:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    total = int(
        await session.scalar(
            select(func.count(SyncJob.id)).where(SyncJob.integration_id == row.id)
        )
        or 0
    )
    rows = (
        await session.scalars(
            select(SyncJob)
            .where(SyncJob.integration_id == row.id)
            .order_by(SyncJob.created_at.desc())
            .limit(limit)
        )
    ).all()
    return SyncJobListResponse(
        items=[SyncJobRead.model_validate(j.__dict__) for j in rows], total=total
    )


@router.get(
    "/api/integrations/{integration_id}/logs",
    response_model=SyncLogListResponse,
    summary="Recent sync logs for an integration",
)
async def list_logs(
    integration_id: uuid.UUID,
    limit: int = Query(default=100, ge=1, le=500),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> SyncLogListResponse:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    total = int(
        await session.scalar(
            select(func.count(SyncLog.id)).where(SyncLog.integration_id == row.id)
        )
        or 0
    )
    rows = (
        await session.scalars(
            select(SyncLog)
            .where(SyncLog.integration_id == row.id)
            .order_by(SyncLog.created_at.desc())
            .limit(limit)
        )
    ).all()
    return SyncLogListResponse(
        items=[SyncLogRead.model_validate(l.__dict__) for l in rows], total=total
    )


# ─────────────────── health, refresh & analytics (R5) ───────────────────

@router.get(
    "/api/integrations/{integration_id}/health",
    response_model=IntegrationHealth,
    summary="Probe an integration's connectivity / credential health",
)
async def integration_health(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> IntegrationHealth:
    from datetime import datetime, timezone

    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    token_expired = bool(
        row.token_expires_at
        and row.token_expires_at <= datetime.now(timezone.utc)
    )

    detail: Optional[str] = None
    status_label = row.status.value
    healthy = row.status == IntegrationStatus.connected and not token_expired

    if row.status == IntegrationStatus.connected and not token_expired:
        # Best-effort live probe — never let a provider failure 500 the API.
        try:
            registry.get_connector(row).health()
            detail = "Connector reachable."
        except ConnectorError as e:
            healthy = False
            status_label = IntegrationStatus.error.value
            detail = str(e)
    elif token_expired:
        status_label = "token_expired"
        detail = "Access token expired — reconnect or refresh."

    return IntegrationHealth(
        provider=row.provider,
        status=status_label,
        healthy=healthy,
        token_expires_at=row.token_expires_at,
        token_expired=token_expired,
        last_synced_at=row.last_synced_at,
        last_error=row.last_error,
        detail=detail,
    )


@router.post(
    "/api/integrations/{integration_id}/refresh",
    response_model=IntegrationRead,
    summary="Refresh an integration's OAuth access token",
    dependencies=[Depends(require_role("owner", "admin"))],
)
async def refresh_integration(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> IntegrationRead:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")
    if row.status == IntegrationStatus.disconnected:
        raise HTTPException(status_code=409, detail="Integration is not connected.")

    try:
        result = registry.get_connector(row).refresh_token()
    except ConnectorError as e:
        row.status = IntegrationStatus.error
        row.last_error = str(e)
        await session.commit()
        raise HTTPException(status_code=502, detail=f"Token refresh failed: {e}") from e

    if result.access_token:
        row.access_token = crypto.encrypt(result.access_token)
    if result.refresh_token:
        row.refresh_token = crypto.encrypt(result.refresh_token)
    if result.token_expires_at:
        row.token_expires_at = result.token_expires_at
    row.status = IntegrationStatus.connected
    row.last_error = None
    await session.commit()
    await session.refresh(row)

    audit(
        "token_refreshed",
        resource="integration",
        resource_id=str(row.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"provider": row.provider},
    )
    return IntegrationRead.model_validate(row.__dict__)


@router.get(
    "/api/integrations/{integration_id}/analytics",
    response_model=IntegrationAnalytics,
    summary="Aggregate sync metrics for an integration",
)
async def integration_analytics(
    integration_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> IntegrationAnalytics:
    row = await _integration_for_org(
        session, integration_id=integration_id, organization_id=ctx.organization_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found.")

    agg = (
        await session.execute(
            select(
                func.count(SyncJob.id),
                func.coalesce(func.sum(SyncJob.documents_synced), 0),
                func.coalesce(func.sum(SyncJob.documents_deleted), 0),
                func.coalesce(func.sum(SyncJob.errors), 0),
                func.avg(
                    func.extract("epoch", SyncJob.finished_at)
                    - func.extract("epoch", SyncJob.started_at)
                ),
            ).where(SyncJob.integration_id == row.id)
        )
    ).one()
    total_jobs, docs_synced, docs_deleted, errors_total, avg_seconds = agg

    successful = int(
        await session.scalar(
            select(func.count(SyncJob.id))
            .where(SyncJob.integration_id == row.id)
            .where(SyncJob.status == SyncJobStatus.completed)
        )
        or 0
    )
    failed = int(
        await session.scalar(
            select(func.count(SyncJob.id))
            .where(SyncJob.integration_id == row.id)
            .where(SyncJob.status == SyncJobStatus.failed)
        )
        or 0
    )
    documents_imported = int(
        await session.scalar(
            select(func.count(Document.id))
            .where(Document.integration_id == row.id)
            .where(Document.deleted_at.is_(None))
        )
        or 0
    )

    recent = (
        await session.scalars(
            select(SyncJob)
            .where(SyncJob.integration_id == row.id)
            .order_by(SyncJob.created_at.desc())
            .limit(5)
        )
    ).all()

    return IntegrationAnalytics(
        provider=row.provider,
        status=row.status.value,
        documents_imported=documents_imported,
        total_sync_jobs=int(total_jobs or 0),
        successful_syncs=successful,
        failed_syncs=failed,
        documents_synced_total=int(docs_synced or 0),
        documents_deleted_total=int(docs_deleted or 0),
        errors_total=int(errors_total or 0),
        last_synced_at=row.last_synced_at,
        avg_sync_seconds=round(float(avg_seconds), 2) if avg_seconds is not None else None,
        recent_jobs=[SyncJobRead.model_validate(j.__dict__) for j in recent],
    )
