"""Sync service (Phase 10).

Orchestrates one integration sync end-to-end:

    connector.sync()  →  upsert Documents (storage + Postgres)
                      →  process_document() [chunk + embed → KB]
                      →  prune documents deleted upstream
                      →  finalize SyncJob + SyncLog + audit

Runs in its own ``AsyncSession`` so it's safe to call from FastAPI
``BackgroundTasks``. Tenant-safe: every row it writes is stamped with the
integration's ``organization_id``; it only ever touches documents that
belong to *this* integration.
"""
from __future__ import annotations

import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import delete, select

from app.connectors.base import ConnectorError, NotConnectedError, RemoteDocument
from app.connectors.registry import get_connector
from app.core import crypto
from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.integration import Integration, IntegrationStatus
from app.database.models.integration_document import (
    IntegrationDocStatus,
    IntegrationDocument,
)
from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.database.models.sync_job import SyncJob, SyncJobStatus, SyncTrigger
from app.database.models.sync_log import SyncLog, SyncLogLevel
from app.database.session import AsyncSessionLocal, init_engine
from app.services import storage
from app.services.audit import audit
from app.services.document_processing import process_document

log = logging.getLogger("app.sync")


async def run_sync(
    integration_id: uuid.UUID,
    *,
    trigger: SyncTrigger = SyncTrigger.manual,
    job_id: Optional[uuid.UUID] = None,
) -> None:
    """Entry point for a background sync. Owns its own DB session."""
    if AsyncSessionLocal is None:
        init_engine()
    from app.database.session import AsyncSessionLocal as Maker

    async with Maker() as session:  # type: ignore[misc]
        await _run(session, integration_id, trigger=trigger, job_id=job_id)


async def _log(
    session,
    job: SyncJob,
    integration: Integration,
    event: str,
    *,
    level: SyncLogLevel = SyncLogLevel.info,
    message: Optional[str] = None,
) -> None:
    session.add(
        SyncLog(
            job_id=job.id,
            integration_id=integration.id,
            organization_id=integration.organization_id,
            event=event,
            level=level,
            message=message,
        )
    )
    await session.flush()


async def _ensure_kb(session, integration: Integration) -> KnowledgeBase:
    """Return the integration's target KB, creating one on first sync."""
    if integration.knowledge_base_id:
        kb = await session.get(KnowledgeBase, integration.knowledge_base_id)
        if kb is not None and kb.deleted_at is None:
            return kb
    kb = KnowledgeBase(
        organization_id=integration.organization_id,
        name=f"{integration.provider.replace('_', ' ').title()} (synced)",
        description=f"Auto-synced from {integration.provider}.",
        status=KnowledgeBaseStatus.active,
    )
    session.add(kb)
    await session.flush()
    integration.knowledge_base_id = kb.id
    return kb


async def _refresh_if_needed(session, integration: Integration) -> None:
    """Refresh the access token if it's expired and a refresh path exists."""
    exp = integration.token_expires_at
    if exp is None:
        return
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp > datetime.now(timezone.utc):
        return
    try:
        connector = get_connector(integration)
        result = connector.refresh_token()
    except (ConnectorError, Exception) as e:  # noqa: BLE001 — degrade
        log.info("token refresh skipped/failed for %s: %s", integration.provider, e)
        return
    if result.access_token:
        integration.access_token = crypto.encrypt(result.access_token)
    if result.refresh_token:
        integration.refresh_token = crypto.encrypt(result.refresh_token)
    if result.token_expires_at:
        integration.token_expires_at = result.token_expires_at
    await session.flush()
    audit(
        "token_refresh",
        resource="integration",
        resource_id=str(integration.id),
        organization_id=str(integration.organization_id),
        user_id="system",
        meta={"provider": integration.provider},
    )


async def _run(
    session,
    integration_id: uuid.UUID,
    *,
    trigger: SyncTrigger,
    job_id: Optional[uuid.UUID],
) -> None:
    integration = await session.get(Integration, integration_id)
    if integration is None or integration.deleted_at is not None:
        log.warning("sync_skip missing_or_deleted integration_id=%s", integration_id)
        return

    # Reuse a pre-created job row (so the API can return its id) or make one.
    job: Optional[SyncJob] = None
    if job_id is not None:
        job = await session.get(SyncJob, job_id)
    if job is None:
        job = SyncJob(
            integration_id=integration.id,
            organization_id=integration.organization_id,
            trigger=trigger,
        )
        session.add(job)
        await session.flush()

    job.status = SyncJobStatus.running
    job.started_at = datetime.now(timezone.utc)
    integration.status = IntegrationStatus.syncing
    await session.commit()

    await _log(session, job, integration, "sync_started",
               message=f"Sync triggered ({trigger.value}).")
    await session.commit()

    try:
        await _refresh_if_needed(session, integration)
        kb = await _ensure_kb(session, integration)
        await session.commit()

        connector = get_connector(integration)
        await _log(session, job, integration, "connector_health",
                   message="Checking connector health.")
        remote_docs = connector.sync()
        await _log(session, job, integration, "fetched",
                   message=f"Fetched {len(remote_docs)} document(s) from provider.")
        await session.commit()

        synced, to_process = await _upsert_documents(
            session, integration, kb, remote_docs, job
        )
        await session.commit()

        # Chunk + embed each new/changed document (own sessions internally).
        for doc_id in to_process:
            await process_document(doc_id)
        if to_process:
            await _log(session, job, integration, "indexed",
                       message=f"Chunked + embedded {len(to_process)} document(s).")

        deleted = await _prune_deleted(session, integration, kb, synced, job)
        await session.commit()

        await _record_manifest(session, integration, remote_docs, synced, job)
        await session.commit()

        job.status = SyncJobStatus.completed
        job.finished_at = datetime.now(timezone.utc)
        job.documents_synced = len(to_process)
        job.documents_deleted = deleted
        integration.status = IntegrationStatus.connected
        integration.last_synced_at = datetime.now(timezone.utc)
        integration.last_error = None
        await _log(session, job, integration, "sync_completed",
                   message=f"Synced {len(to_process)}, removed {deleted}.")
        await session.commit()

        audit(
            "sync_completed",
            resource="integration",
            resource_id=str(integration.id),
            organization_id=str(integration.organization_id),
            user_id="system",
            meta={
                "provider": integration.provider,
                "documents_synced": len(to_process),
                "documents_deleted": deleted,
                "job_id": str(job.id),
            },
        )
        log.info(
            "sync_ok integration=%s provider=%s synced=%d deleted=%d",
            integration.id, integration.provider, len(to_process), deleted,
        )
    except (NotConnectedError, ConnectorError) as e:
        await _fail(session, job.id, integration.id, str(e))
    except Exception as e:  # noqa: BLE001 — capture any failure
        log.exception("sync_failed integration=%s err=%s", integration_id, e)
        await _fail(session, job.id, integration.id, f"{type(e).__name__}: {e}")


async def _upsert_documents(
    session,
    integration: Integration,
    kb: KnowledgeBase,
    remote_docs: list[RemoteDocument],
    job: SyncJob,
) -> tuple[set[str], list[uuid.UUID]]:
    """Create/update Document rows for remote docs. Returns
    (set of external_ids seen, list of document ids needing processing)."""
    seen: set[str] = set()
    to_process: list[uuid.UUID] = []

    for rd in remote_docs:
        seen.add(rd.external_id)
        existing = await session.scalar(
            select(Document)
            .where(Document.integration_id == integration.id)
            .where(Document.external_id == rd.external_id)
            .where(Document.deleted_at.is_(None))
        )

        # Skip unchanged (same or older upstream modified time, already processed).
        if (
            existing is not None
            and existing.status == DocumentStatus.processed
            and existing.external_modified_at is not None
            and rd.modified_at is not None
            and _aware(rd.modified_at) <= _aware(existing.external_modified_at)
        ):
            continue

        data = rd.as_bytes()
        key = (
            f"org/{integration.organization_id}/integration/{integration.provider}/"
            f"{rd.external_id}__{_safe(rd.filename)}"
        )
        s3_key = storage.put_object(
            key=key, body=io.BytesIO(data), content_type=rd.mime_type
        )

        if existing is None:
            doc = Document(
                knowledge_base_id=kb.id,
                organization_id=integration.organization_id,
                project_id=kb.project_id,
                filename=rd.filename,
                file_type=rd.mime_type,
                file_size=len(data),
                s3_key=s3_key,
                status=DocumentStatus.pending,
                source=integration.provider,
                integration_id=integration.id,
                external_id=rd.external_id,
                external_modified_at=_aware(rd.modified_at) if rd.modified_at else None,
            )
            session.add(doc)
            await session.flush()
            to_process.append(doc.id)
        else:
            existing.filename = rd.filename
            existing.file_type = rd.mime_type
            existing.file_size = len(data)
            existing.s3_key = s3_key
            existing.status = DocumentStatus.pending
            existing.external_modified_at = (
                _aware(rd.modified_at) if rd.modified_at else None
            )
            await session.flush()
            to_process.append(existing.id)

    return seen, to_process


async def _prune_deleted(
    session,
    integration: Integration,
    kb: KnowledgeBase,
    seen: set[str],
    job: SyncJob,
) -> int:
    """Soft-delete documents that no longer exist upstream + drop their chunks."""
    rows = (
        await session.scalars(
            select(Document)
            .where(Document.integration_id == integration.id)
            .where(Document.deleted_at.is_(None))
        )
    ).all()
    deleted = 0
    for doc in rows:
        if doc.external_id in seen:
            continue
        await session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )
        doc.deleted_at = datetime.now(timezone.utc)
        deleted += 1
    if deleted:
        await _log(session, job, integration, "pruned",
                   message=f"Removed {deleted} document(s) deleted upstream.")
    return deleted


async def _record_manifest(
    session,
    integration: Integration,
    remote_docs: list[RemoteDocument],
    seen: set[str],
    job: SyncJob,
) -> None:
    """Reconcile the ``integration_documents`` manifest after a sync.

    Upserts a row per resolved remote file (status=synced, checksum, path,
    document link) and marks previously-synced file rows that disappeared
    upstream / were deselected as ``removed``.
    """
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

    # Map external_id → Document id for the docs we just upserted.
    doc_rows = (
        await session.scalars(
            select(Document)
            .where(Document.integration_id == integration.id)
            .where(Document.deleted_at.is_(None))
        )
    ).all()
    doc_by_ext = {d.external_id: d for d in doc_rows if d.external_id}

    now = datetime.now(timezone.utc)
    for rd in remote_docs:
        meta = rd.metadata or {}
        size = None
        try:
            size = int(meta.get("size")) if meta.get("size") else len(rd.as_bytes())
        except (TypeError, ValueError):
            size = len(rd.as_bytes())
        doc = doc_by_ext.get(rd.external_id)
        item = existing.get(rd.external_id)
        if item is None:
            session.add(
                IntegrationDocument(
                    integration_id=integration.id,
                    organization_id=integration.organization_id,
                    external_id=rd.external_id,
                    name=rd.name or rd.external_id,
                    mime_type=rd.mime_type,
                    path=meta.get("path"),
                    is_folder=False,
                    selected=True,
                    status=IntegrationDocStatus.synced,
                    checksum=rd.content_hash(),
                    size_bytes=size,
                    external_modified_at=_aware(rd.modified_at) if rd.modified_at else None,
                    last_synced=now,
                    document_id=doc.id if doc is not None else None,
                )
            )
        else:
            item.name = rd.name or item.name
            item.mime_type = rd.mime_type
            item.path = meta.get("path") or item.path
            item.is_folder = False
            item.selected = True
            item.status = IntegrationDocStatus.synced
            item.checksum = rd.content_hash()
            item.size_bytes = size
            item.external_modified_at = (
                _aware(rd.modified_at) if rd.modified_at else item.external_modified_at
            )
            item.last_synced = now
            if doc is not None:
                item.document_id = doc.id

    # Mark previously-synced FILE rows that vanished upstream / deselected.
    for ext_id, item in existing.items():
        if item.is_folder:
            continue
        if ext_id not in seen and item.status == IntegrationDocStatus.synced:
            item.status = IntegrationDocStatus.removed
            item.selected = False
    await session.flush()


async def _fail(session, job_id: uuid.UUID, integration_id: uuid.UUID, message: str) -> None:
    # Roll back any partial work, then re-fetch by id (objects are expired
    # after rollback — never touch the stale instances directly).
    await session.rollback()
    job = await session.get(SyncJob, job_id)
    integration = await session.get(Integration, integration_id)
    if job is not None:
        job.status = SyncJobStatus.failed
        job.finished_at = datetime.now(timezone.utc)
        job.errors = (job.errors or 0) + 1
        job.error_message = message[:2000]
    if integration is not None:
        integration.status = IntegrationStatus.error
        integration.last_error = message[:1000]
        session.add(
            SyncLog(
                job_id=job_id if job else None,
                integration_id=integration.id,
                organization_id=integration.organization_id,
                event="sync_failed",
                level=SyncLogLevel.error,
                message=message[:2000],
            )
        )
    await session.commit()
    if integration is not None:
        audit(
            "sync_failed",
            resource="integration",
            resource_id=str(integration_id),
            organization_id=str(integration.organization_id),
            user_id="system",
            meta={"provider": integration.provider, "error": message[:300]},
        )
    log.warning("sync_failed_recorded integration=%s msg=%s", integration_id, message)


def _safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:180]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
