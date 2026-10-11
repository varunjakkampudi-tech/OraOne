"""RAG Query API (R4).

Endpoints
---------
* ``POST /api/rag/query``   — grounded answer + citations + confidence + follow-ups
* ``POST /api/rag/search``  — raw hybrid-search hits (no generation)
* ``GET  /api/rag/sources`` — counts of searchable sources for the tenant

All endpoints are tenant-scoped via :class:`OrgContext`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.document import Document, DocumentStatus
from app.database.models.document_chunk import DocumentChunk
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.website import Website
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagSearchHit,
    RagSearchRequest,
    RagSearchResponse,
    RagSourcesResponse,
)
from app.services import rag_service
from app.services.audit import audit
from app.services.rag_answer import answer_query

router = APIRouter(tags=["rag"])


@router.post(
    "/api/rag/query",
    response_model=RagQueryResponse,
    summary="Answer a question from the knowledge base (RAG)",
)
async def rag_query(
    payload: RagQueryRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RagQueryResponse:
    result = await answer_query(
        session,
        payload.query,
        ctx.organization_id,
        knowledge_base_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        source_types=payload.source_types,
    )
    audit(
        "query",
        resource="rag",
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        meta={
            "chunks": result["context_chunks"],
            "confidence": result["confidence"],
            "grounded": result["grounded"],
        },
    )
    return RagQueryResponse(**result)


@router.post(
    "/api/rag/search",
    response_model=RagSearchResponse,
    summary="Hybrid search over knowledge chunks (no answer generation)",
)
async def rag_search(
    payload: RagSearchRequest,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RagSearchResponse:
    chunks = await rag_service.hybrid_search(
        session,
        payload.query,
        ctx.organization_id,
        knowledge_base_ids=payload.knowledge_base_ids,
        top_k=payload.top_k,
        source_types=payload.source_types,
    )
    hits = [
        RagSearchHit(
            content=c.content,
            score=c.score,
            source_type=c.source_type,
            title=c.title,
            url=c.url,
            page=c.page,
            section=c.section,
            chunk_index=c.chunk_index,
            components=c.components,
        )
        for c in chunks
    ]
    return RagSearchResponse(hits=hits, count=len(hits))


@router.get(
    "/api/rag/sources",
    response_model=RagSourcesResponse,
    summary="Counts of searchable sources for the tenant",
)
async def rag_sources(
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> RagSourcesResponse:
    docs = int(
        await session.scalar(
            select(func.count(Document.id))
            .where(Document.organization_id == ctx.organization_id)
            .where(Document.deleted_at.is_(None))
            .where(Document.status == DocumentStatus.processed)
        )
        or 0
    )
    sites = int(
        await session.scalar(
            select(func.count(Website.id))
            .where(Website.organization_id == ctx.organization_id)
            .where(Website.deleted_at.is_(None))
        )
        or 0
    )
    chunks = int(
        await session.scalar(
            select(func.count(DocumentChunk.id)).where(
                DocumentChunk.organization_id == ctx.organization_id
            )
        )
        or 0
    )
    kbs = int(
        await session.scalar(
            select(func.count(KnowledgeBase.id))
            .where(KnowledgeBase.organization_id == ctx.organization_id)
            .where(KnowledgeBase.deleted_at.is_(None))
        )
        or 0
    )
    return RagSourcesResponse(documents=docs, websites=sites, chunks=chunks, knowledge_bases=kbs)
