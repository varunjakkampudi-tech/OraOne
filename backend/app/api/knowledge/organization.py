"""R2 Enterprise Knowledge: folders, document organization, search, preview,
versions, and bulk actions. Mounted alongside the Phase 6 knowledge router.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.document_version import DocumentVersion
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.knowledge_folder import KnowledgeFolder
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.knowledge import (
    BulkAction,
    BulkResult,
    DocumentPatch,
    DocumentPreview,
    DocumentRead,
    DocumentVersionOut,
    KnowledgeFolderCreate,
    KnowledgeFolderOut,
    KnowledgeFolderUpdate,
    KnowledgeSearchHit,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.services import rag_service
from app.services.audit import audit
from app.services.document_processing import process_document

router = APIRouter(tags=["knowledge-organization"])


def _norm_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    for t in tags or []:
        t = (t or "").strip()[:40]
        if t and t not in out:
            out.append(t)
    return out[:20]


async def _doc_chunk_count(session: AsyncSession, doc_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_id)
        )
        or 0
    )


def _doc_to_read(doc: Document, *, chunk_count: int) -> DocumentRead:
    elapsed_ms = None
    if doc.processing_started_at and doc.processing_completed_at:
        elapsed_ms = int(
            (doc.processing_completed_at - doc.processing_started_at).total_seconds() * 1000
        )
    return DocumentRead.model_validate(
        {**doc.__dict__, "chunk_count": chunk_count, "processing_time_ms": elapsed_ms}
    )


async def _load_doc(session: AsyncSession, ctx: OrgContext, doc_id: uuid.UUID) -> Optional[Document]:
    return await session.scalar(
        select(Document)
        .where(Document.id == doc_id)
        .where(Document.organization_id == ctx.organization_id)
        .where(Document.deleted_at.is_(None))
    )


# ─────────────────────── Knowledge folders ───────────────────────

async def _folder_doc_count(session: AsyncSession, folder_id: uuid.UUID) -> int:
    return int(
        await session.scalar(
            select(func.count(Document.id))
            .where(Document.folder_id == folder_id)
            .where(Document.deleted_at.is_(None))
        )
        or 0
    )


async def _folder_out(session: AsyncSession, f: KnowledgeFolder) -> KnowledgeFolderOut:
    return KnowledgeFolderOut(
        id=f.id,
        knowledge_base_id=f.knowledge_base_id,
        parent_folder_id=f.parent_folder_id,
        name=f.name,
        color=f.color,
        document_count=await _folder_doc_count(session, f.id),
        created_at=f.created_at,
        updated_at=f.updated_at,
    )


@router.get("/api/knowledge-folders", response_model=list[KnowledgeFolderOut])
async def list_knowledge_folders(
    knowledge_base_id: uuid.UUID = Query(...),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[KnowledgeFolderOut]:
    rows = list(
        (
            await session.scalars(
                select(KnowledgeFolder)
                .where(KnowledgeFolder.organization_id == ctx.organization_id)
                .where(KnowledgeFolder.knowledge_base_id == knowledge_base_id)
                .order_by(KnowledgeFolder.name.asc())
            )
        ).all()
    )
    return [await _folder_out(session, f) for f in rows]


@router.post("/api/knowledge-folders", response_model=KnowledgeFolderOut, status_code=status.HTTP_201_CREATED)
async def create_knowledge_folder(
    payload: KnowledgeFolderCreate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeFolderOut:
    kb = await session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == payload.knowledge_base_id)
        .where(KnowledgeBase.organization_id == ctx.organization_id)
        .where(KnowledgeBase.deleted_at.is_(None))
    )
    if kb is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found.")
    if payload.parent_folder_id is not None:
        parent = await session.scalar(
            select(KnowledgeFolder)
            .where(KnowledgeFolder.id == payload.parent_folder_id)
            .where(KnowledgeFolder.knowledge_base_id == kb.id)
            .where(KnowledgeFolder.organization_id == ctx.organization_id)
        )
        if parent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Parent folder not found.")
    folder = KnowledgeFolder(
        knowledge_base_id=kb.id,
        organization_id=ctx.organization_id,
        parent_folder_id=payload.parent_folder_id,
        name=payload.name.strip(),
        color=payload.color,
    )
    session.add(folder)
    await session.commit()
    await session.refresh(folder)
    audit(
        "create",
        resource="knowledge_folder",
        resource_id=str(folder.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"name": folder.name},
    )
    return await _folder_out(session, folder)


@router.put("/api/knowledge-folders/{folder_id}", response_model=KnowledgeFolderOut)
async def update_knowledge_folder(
    folder_id: uuid.UUID,
    payload: KnowledgeFolderUpdate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeFolderOut:
    folder = await session.scalar(
        select(KnowledgeFolder)
        .where(KnowledgeFolder.id == folder_id)
        .where(KnowledgeFolder.organization_id == ctx.organization_id)
    )
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    if payload.name is not None:
        folder.name = payload.name.strip()
    if payload.color is not None:
        folder.color = payload.color
    if payload.parent_folder_id is not None and payload.parent_folder_id != folder.id:
        folder.parent_folder_id = payload.parent_folder_id
    await session.commit()
    await session.refresh(folder)
    return await _folder_out(session, folder)


@router.delete("/api/knowledge-folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_folder(
    folder_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
):
    folder = await session.scalar(
        select(KnowledgeFolder)
        .where(KnowledgeFolder.id == folder_id)
        .where(KnowledgeFolder.organization_id == ctx.organization_id)
    )
    if folder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    # Detach documents (keep them) and reparent child folders to root.
    await session.execute(
        update(Document).where(Document.folder_id == folder_id).values(folder_id=None)
    )
    await session.execute(
        update(KnowledgeFolder)
        .where(KnowledgeFolder.parent_folder_id == folder_id)
        .values(parent_folder_id=None)
    )
    await session.delete(folder)
    await session.commit()
    audit(
        "delete",
        resource="knowledge_folder",
        resource_id=str(folder_id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return None


# ─────────────────────── Document organization ───────────────────────

@router.patch("/api/documents/{document_id}", response_model=DocumentRead)
async def patch_document(
    document_id: uuid.UUID,
    payload: DocumentPatch,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    """Move a document to a folder / clear folder / set tags."""
    doc = await _load_doc(session, ctx, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    changed: dict = {}
    if payload.tags is not None:
        doc.tags = _norm_tags(payload.tags)
        changed["tags"] = doc.tags
    if payload.clear_folder:
        doc.folder_id = None
        changed["folder_id"] = None
    elif payload.folder_id is not None:
        folder = await session.scalar(
            select(KnowledgeFolder)
            .where(KnowledgeFolder.id == payload.folder_id)
            .where(KnowledgeFolder.knowledge_base_id == doc.knowledge_base_id)
            .where(KnowledgeFolder.organization_id == ctx.organization_id)
        )
        if folder is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
        doc.folder_id = folder.id
        changed["folder_id"] = str(folder.id)
    await session.commit()
    await session.refresh(doc)
    audit(
        "update",
        resource="document",
        resource_id=str(doc.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta=changed,
    )
    return _doc_to_read(doc, chunk_count=await _doc_chunk_count(session, doc.id))


@router.post("/api/documents/bulk", response_model=BulkResult)
async def bulk_documents(
    payload: BulkAction,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> BulkResult:
    """Apply an action to many documents: delete | move | tag | reprocess."""
    docs = list(
        (
            await session.scalars(
                select(Document)
                .where(Document.id.in_(payload.document_ids))
                .where(Document.organization_id == ctx.organization_id)
                .where(Document.deleted_at.is_(None))
            )
        ).all()
    )
    if not docs:
        return BulkResult(affected=0, action=payload.action)

    from datetime import datetime, timezone

    action = payload.action
    if action == "delete":
        for d in docs:
            d.deleted_at = datetime.now(timezone.utc)
    elif action == "move":
        target = None
        if not payload.clear_folder and payload.folder_id is not None:
            target = await session.scalar(
                select(KnowledgeFolder)
                .where(KnowledgeFolder.id == payload.folder_id)
                .where(KnowledgeFolder.organization_id == ctx.organization_id)
            )
            if target is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
        for d in docs:
            d.folder_id = None if payload.clear_folder else (target.id if target else None)
    elif action == "tag":
        tags = _norm_tags(payload.tags or [])
        for d in docs:
            d.tags = tags
    elif action == "reprocess":
        for d in docs:
            d.status = DocumentStatus.pending
            d.processing_error = None
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown action: {action}")

    await session.commit()
    if action == "reprocess":
        import asyncio

        for d in docs:
            # Detached task — process_document owns its own session.
            asyncio.create_task(process_document(d.id))

    audit(
        f"bulk_{action}",
        resource="document",
        resource_id=",".join(str(d.id) for d in docs[:20]),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"count": len(docs)},
    )
    return BulkResult(affected=len(docs), action=action)


@router.get("/api/documents/{document_id}/preview", response_model=DocumentPreview)
async def preview_document(
    document_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> DocumentPreview:
    doc = await _load_doc(session, ctx, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    # Excerpt: first few chunks joined (already-extracted text, no re-IO).
    rows = list(
        (
            await session.scalars(
                select(DocumentChunk.content)
                .where(DocumentChunk.document_id == doc.id)
                .order_by(DocumentChunk.chunk_index.asc())
                .limit(3)
            )
        ).all()
    )
    excerpt = "\n\n".join(rows)[:1500]
    return DocumentPreview(
        id=doc.id,
        filename=doc.filename,
        summary=doc.summary,
        suggested_questions=doc.suggested_questions or [],
        tags=doc.tags or [],
        doc_metadata=doc.doc_metadata or {},
        excerpt=excerpt,
    )


@router.get("/api/documents/{document_id}/versions", response_model=list[DocumentVersionOut])
async def list_document_versions(
    document_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> list[DocumentVersionOut]:
    doc = await _load_doc(session, ctx, document_id)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found.")
    rows = list(
        (
            await session.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == doc.id)
                .where(DocumentVersion.organization_id == ctx.organization_id)
                .order_by(DocumentVersion.version.desc())
            )
        ).all()
    )
    return [DocumentVersionOut.model_validate(v) for v in rows]


# ─────────────────────── Knowledge search ───────────────────────

@router.post("/api/knowledge/search", response_model=KnowledgeSearchResponse)
async def knowledge_search(
    payload: KnowledgeSearchRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeSearchResponse:
    """Semantic + keyword search across processed documents (org-scoped)."""
    kb_ids = [payload.knowledge_base_id] if payload.knowledge_base_id else None
    chunks = await rag_service.search_chunks(
        session,
        payload.query,
        ctx.organization_id,
        knowledge_base_ids=kb_ids,
        top_k=payload.top_k,
    )
    audit(
        "search",
        resource="knowledge",
        resource_id=str(payload.knowledge_base_id) if payload.knowledge_base_id else None,
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={"query": payload.query[:120], "hits": len(chunks)},
    )
    hits = [
        KnowledgeSearchHit(
            document_id=c.document_id,
            website_page_id=c.website_page_id,
            document=c.title,
            url=c.url,
            source_type=c.source_type,
            content=c.content[:600],
            page=c.page,
            section=c.section,
            score=round(c.score, 4) if c.score is not None else None,
        )
        for c in chunks
    ]
    return KnowledgeSearchResponse(query=payload.query, hits=hits)
