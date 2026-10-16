"""Knowledge Studio — multi-source ingestion (Phase R).

The existing knowledge API ingests **uploaded files**. This module adds the
other two sources every knowledge base needs:

* ``website`` — fetch a public web page and ingest its content.
* ``text``    — paste raw text / FAQ content directly.

Both reuse the *exact* same downstream pipeline as file upload: we persist a
``documents`` row (stored via :mod:`app.services.storage`) and hand it to
:func:`process_document`, which chunks + embeds it. No new RAG logic.

Security: the website fetcher is SSRF-guarded — only ``http``/``https`` public
hosts are allowed; loopback, private, link-local and reserved IPs are rejected.
"""

from __future__ import annotations

import uuid
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.document import Document, DocumentStatus
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.knowledge_folder import KnowledgeFolder
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.schemas.knowledge import DocumentRead
from app.services import storage
from app.services.audit import audit
from app.services.document_processing import compute_checksum, process_document
from app.services.website_crawler import URLValidationError, validate_url

router = APIRouter(tags=["knowledge-sources"])

_MAX_FETCH_BYTES = 5 * 1024 * 1024  # 5 MB cap on a fetched page
_FETCH_TIMEOUT = 15.0

SOURCE_TYPES = [
    {
        "value": "file",
        "label": "File upload",
        "description": "PDF, DOCX, TXT, CSV, XLSX, PPTX, MD.",
    },
    {
        "value": "website",
        "label": "Website URL",
        "description": "Crawl a public web page into the knowledge base.",
    },
    {
        "value": "text",
        "label": "Text / FAQ",
        "description": "Paste raw text or Q&A content directly.",
    },
]


# ─────────────────────────────── schemas ─────────────────────────────────────


class WebsiteSourceIn(BaseModel):
    knowledge_base_id: uuid.UUID
    url: str = Field(..., min_length=4, max_length=2000)
    folder_id: Optional[uuid.UUID] = None


class TextSourceIn(BaseModel):
    knowledge_base_id: uuid.UUID
    title: str = Field(..., min_length=1, max_length=300)
    content: str = Field(..., min_length=1, max_length=500_000)
    folder_id: Optional[uuid.UUID] = None


# ─────────────────────────────── helpers ─────────────────────────────────────


def _guard_public_url(raw: str) -> str:
    """Validate a URL is a public http(s) endpoint (SSRF protection)."""
    try:
        return validate_url(raw)
    except URLValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


async def _fetch_public_page(raw_url: str) -> tuple[str, str, bytes]:
    """Fetch a bounded public page while validating every redirect hop.

    Following redirects in ``httpx`` without inspecting each target allows a
    public URL to redirect the backend into loopback, private, or cloud
    metadata networks. The URL validator is therefore applied before every
    request. Streaming also prevents a hostile response from allocating an
    unbounded body before the size cap is enforced.
    """
    current = _guard_public_url(raw_url)
    async with httpx.AsyncClient(
        follow_redirects=False, timeout=_FETCH_TIMEOUT
    ) as client:
        for _ in range(5):
            try:
                async with client.stream(
                    "GET", current, headers={"User-Agent": "OraOneBot/1.0"}
                ) as resp:
                    if resp.status_code in {301, 302, 303, 307, 308}:
                        location = resp.headers.get("location")
                        if not location:
                            raise HTTPException(
                                status_code=502,
                                detail="Redirect response has no location.",
                            )
                        try:
                            current = validate_url(urljoin(current, location))
                        except URLValidationError as exc:
                            raise HTTPException(
                                status_code=422, detail=str(exc)
                            ) from exc
                        continue

                    resp.raise_for_status()
                    content_length = resp.headers.get("content-length")
                    if content_length and int(content_length) > _MAX_FETCH_BYTES:
                        raise HTTPException(
                            status_code=413, detail="The page is too large to ingest."
                        )

                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in resp.aiter_bytes():
                        total += len(chunk)
                        if total > _MAX_FETCH_BYTES:
                            raise HTTPException(
                                status_code=413,
                                detail="The page is too large to ingest.",
                            )
                        chunks.append(chunk)
                    return (
                        current,
                        resp.headers.get("content-type", "text/html"),
                        b"".join(chunks),
                    )
            except HTTPException:
                raise
            except (httpx.HTTPError, ValueError) as exc:
                raise HTTPException(
                    status_code=502, detail="Could not fetch the page safely."
                ) from exc

    raise HTTPException(
        status_code=502, detail="Too many redirects while fetching the page."
    )


async def _kb_for_org(
    session: AsyncSession, *, kb_id: uuid.UUID, organization_id: uuid.UUID
) -> KnowledgeBase:
    kb = await session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == kb_id)
        .where(KnowledgeBase.organization_id == organization_id)
        .where(KnowledgeBase.deleted_at.is_(None))
    )
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found.")
    return kb


async def _validate_folder(
    session: AsyncSession,
    *,
    folder_id: Optional[uuid.UUID],
    kb: KnowledgeBase,
    organization_id: uuid.UUID,
) -> None:
    if folder_id is None:
        return
    folder = await session.scalar(
        select(KnowledgeFolder)
        .where(KnowledgeFolder.id == folder_id)
        .where(KnowledgeFolder.knowledge_base_id == kb.id)
        .where(KnowledgeFolder.organization_id == organization_id)
    )
    if folder is None:
        raise HTTPException(status_code=404, detail="Folder not found.")


async def _ingest(
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    *,
    kb: KnowledgeBase,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    filename: str,
    content_type: str,
    body: bytes,
    folder_id: Optional[uuid.UUID],
    source: str,
    source_ref: str,
) -> DocumentRead:
    """Persist + process a synthesised document body. Mirrors file upload."""
    checksum = compute_checksum(body)

    dup = await session.scalar(
        select(Document)
        .where(Document.knowledge_base_id == kb.id)
        .where(Document.checksum == checksum)
        .where(Document.deleted_at.is_(None))
    )
    if dup is not None:
        return DocumentRead.model_validate(
            {**dup.__dict__, "chunk_count": 0, "embedded_count": 0}
        )

    from io import BytesIO

    key = storage.build_key(
        organization_id=str(organization_id),
        knowledge_base_id=str(kb.id),
        filename=filename,
    )
    storage_key = storage.put_object(
        key=key, body=BytesIO(body), content_type=content_type
    )

    doc = Document(
        knowledge_base_id=kb.id,
        organization_id=organization_id,
        project_id=kb.project_id,
        filename=filename,
        file_type=content_type,
        file_size=len(body),
        storage_key=storage_key,
        checksum=checksum,
        folder_id=folder_id,
        status=DocumentStatus.pending,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)

    audit(
        "create",
        resource="document",
        resource_id=str(doc.id),
        organization_id=str(organization_id),
        user_id=str(user_id),
        after={"filename": filename, "source": source, "source_ref": source_ref},
    )
    background_tasks.add_task(process_document, doc.id)
    return DocumentRead.model_validate(
        {**doc.__dict__, "chunk_count": 0, "embedded_count": 0}
    )


# ─────────────────────────────── routes ──────────────────────────────────────


@router.get("/api/knowledge/sources/types")
async def list_source_types(
    _ctx: OrgContext = Depends(get_current_organization),
) -> list[dict[str, str]]:
    return SOURCE_TYPES


@router.post(
    "/api/knowledge/sources/website",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_website(
    payload: WebsiteSourceIn,
    background_tasks: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    url = _guard_public_url(payload.url)
    kb = await _kb_for_org(
        session, kb_id=payload.knowledge_base_id, organization_id=ctx.organization_id
    )
    await _validate_folder(
        session, folder_id=payload.folder_id, kb=kb, organization_id=ctx.organization_id
    )

    final_url, response_content_type, body = await _fetch_public_page(url)

    if not body:
        raise HTTPException(status_code=422, detail="The page returned no content.")

    host = urlparse(final_url).hostname or "page"
    content_type = response_content_type.split(";")[0].strip() or "text/html"
    if content_type not in {"text/html", "text/plain", "application/json"}:
        content_type = "text/html"
    filename = f"{host}.html" if content_type == "text/html" else f"{host}.txt"

    return await _ingest(
        session,
        background_tasks,
        kb=kb,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        filename=filename,
        content_type=content_type,
        body=body,
        folder_id=payload.folder_id,
        source="website",
        source_ref=final_url,
    )


@router.post(
    "/api/knowledge/sources/text",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_text(
    payload: TextSourceIn,
    background_tasks: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> DocumentRead:
    kb = await _kb_for_org(
        session, kb_id=payload.knowledge_base_id, organization_id=ctx.organization_id
    )
    await _validate_folder(
        session, folder_id=payload.folder_id, kb=kb, organization_id=ctx.organization_id
    )

    title = payload.title.strip()
    safe = (
        "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:80].strip()
        or "note"
    )
    body = f"# {title}\n\n{payload.content}".encode("utf-8")

    return await _ingest(
        session,
        background_tasks,
        kb=kb,
        organization_id=ctx.organization_id,
        user_id=ctx.user_id,
        filename=f"{safe}.txt",
        content_type="text/plain",
        body=body,
        folder_id=payload.folder_id,
        source="text",
        source_ref=title,
    )
