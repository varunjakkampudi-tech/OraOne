"""Website Crawling API (R3).

Endpoints
---------
* ``POST   /api/websites``                  — register a website + (optionally) start a crawl
* ``GET    /api/websites``                  — list (paginated, filterable)
* ``GET    /api/websites/{id}``             — get one
* ``PUT    /api/websites/{id}``             — partial update
* ``DELETE /api/websites/{id}``             — soft delete (owner/admin)
* ``POST   /api/websites/{id}/crawl``       — start / re-run a crawl (background)
* ``POST   /api/websites/{id}/recrawl``     — alias for crawl (force full re-crawl)
* ``POST   /api/websites/{id}/pause``       — mark paused
* ``POST   /api/websites/{id}/resume``      — mark ready/paused→ready
* ``GET    /api/websites/{id}/pages``       — list crawled pages
* ``GET    /api/websites/{id}/pages/{pid}`` — page detail (markdown)
* ``GET    /api/websites/{id}/jobs``        — crawl job history
* ``GET    /api/websites/{id}/jobs/{jid}/logs`` — crawl logs for a job
* ``GET    /api/websites/{id}/analytics``   — coverage analytics

Crawling runs in a FastAPI background task; the job row is polled by the
UI for live progress. Every URL is SSRF-validated before registration.
"""
from __future__ import annotations

import uuid
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy import asc, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.crawl_frontier import CrawlFrontier, FrontierStatus
from app.database.models.crawl_job import CrawlJob, CrawlJobStatus, CrawlLog, CrawlTrigger
from app.database.models.document_chunk import DocumentChunk
from app.database.models.knowledge_base import KnowledgeBase
from app.database.models.website import (
    CrawlFrequency,
    CrawlMode,
    Website,
    WebsiteStatus,
)
from app.database.models.website_page import PageStatus, WebsitePage
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization, require_role
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.website import (
    CrawlJobListResponse,
    CrawlJobRead,
    CrawlLogListResponse,
    CrawlLogRead,
    WebsiteAnalytics,
    WebsiteCreate,
    WebsiteListResponse,
    WebsitePageDetail,
    WebsitePageListResponse,
    WebsitePageRead,
    WebsiteRead,
    WebsiteUpdate,
)
from app.services.audit import audit
from app.services.website_crawler import URLValidationError, run_crawl, validate_url

router = APIRouter(tags=["websites"])


# ─────────────────── helpers ───────────────────

def _validate_choice(value, allowed: set, field: str):
    if value is not None and value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {field} {value!r}. Allowed: {sorted(allowed)}.",
        )


async def _website_for_org(session, *, website_id, organization_id) -> Optional[Website]:
    return await session.scalar(
        select(Website)
        .where(Website.id == website_id)
        .where(Website.organization_id == organization_id)
        .where(Website.deleted_at.is_(None))
    )


async def _kb_for_org(session, *, kb_id, organization_id) -> Optional[KnowledgeBase]:
    return await session.scalar(
        select(KnowledgeBase)
        .where(KnowledgeBase.id == kb_id)
        .where(KnowledgeBase.organization_id == organization_id)
        .where(KnowledgeBase.deleted_at.is_(None))
    )


async def _start_crawl(
    session: AsyncSession,
    website: Website,
    background: BackgroundTasks,
    *,
    trigger: str = CrawlTrigger.manual,
) -> CrawlJob:
    job = CrawlJob(
        website_id=website.id,
        organization_id=website.organization_id,
        status=CrawlJobStatus.queued,
        trigger=trigger,
    )
    session.add(job)
    website.status = WebsiteStatus.crawling
    website.error = None
    await session.commit()
    await session.refresh(job)
    background.add_task(run_crawl, job.id)
    return job


# ─────────────────── Websites CRUD ───────────────────

@router.post(
    "/api/websites",
    response_model=WebsiteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a website and (optionally) start crawling",
)
async def create_website(
    payload: WebsiteCreate,
    background: BackgroundTasks,
    start: bool = Query(default=True, description="Start an initial crawl immediately"),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    ctx = pctx.org
    _validate_choice(payload.crawl_mode, CrawlMode.ALL, "crawl_mode")
    _validate_choice(payload.crawl_frequency, CrawlFrequency.ALL, "crawl_frequency")

    try:
        base_url = validate_url(payload.base_url)
    except URLValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    kb = await _kb_for_org(session, kb_id=payload.knowledge_base_id, organization_id=ctx.organization_id)
    if kb is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found.")

    name = (payload.name or "").strip() or (urlparse(base_url).hostname or base_url)
    website = Website(
        organization_id=ctx.organization_id,
        project_id=pctx.project_id,
        knowledge_base_id=kb.id,
        name=name[:200],
        base_url=base_url,
        status=WebsiteStatus.pending,
        crawl_mode=payload.crawl_mode,
        max_depth=payload.max_depth,
        max_pages=payload.max_pages,
        crawl_frequency=payload.crawl_frequency,
        respect_robots=payload.respect_robots,
        render_js=payload.render_js,
        crawl_delay_ms=payload.crawl_delay_ms,
        max_concurrency=payload.max_concurrency,
        include_paths=payload.include_paths,
        exclude_paths=payload.exclude_paths,
        allowed_domains=payload.allowed_domains,
        auth_config=payload.auth_config,
    )
    session.add(website)
    await session.commit()
    await session.refresh(website)

    audit(
        "create",
        resource="website",
        resource_id=str(website.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after={"base_url": website.base_url, "crawl_mode": website.crawl_mode},
    )

    if start:
        await _start_crawl(session, website, background)
        await session.refresh(website)

    return WebsiteRead.model_validate(website)


@router.get("/api/websites", response_model=WebsiteListResponse, summary="List websites")
async def list_websites(
    q: Optional[str] = Query(default=None, max_length=200),
    status_: Optional[str] = Query(default=None, alias="status"),
    knowledge_base_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    pctx: ProjectContext = Depends(get_current_project),
    session: AsyncSession = Depends(get_db),
) -> WebsiteListResponse:
    ctx = pctx.org
    base = (
        select(Website)
        .where(Website.organization_id == ctx.organization_id)
        .where(Website.project_id == pctx.project_id)
        .where(Website.deleted_at.is_(None))
    )
    if q:
        like = f"%{q}%"
        base = base.where(or_(Website.name.ilike(like), Website.base_url.ilike(like)))
    if status_:
        base = base.where(Website.status == status_)
    if knowledge_base_id:
        base = base.where(Website.knowledge_base_id == knowledge_base_id)

    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (
        await session.scalars(base.order_by(desc(Website.created_at)).limit(limit).offset(offset))
    ).all()
    return WebsiteListResponse(
        items=[WebsiteRead.model_validate(w) for w in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/api/websites/{website_id}", response_model=WebsiteRead, summary="Get a website")
async def get_website(
    website_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    return WebsiteRead.model_validate(website)


@router.put("/api/websites/{website_id}", response_model=WebsiteRead, summary="Update a website")
async def update_website(
    website_id: uuid.UUID,
    payload: WebsiteUpdate,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    _validate_choice(payload.crawl_mode, CrawlMode.ALL, "crawl_mode")
    _validate_choice(payload.crawl_frequency, CrawlFrequency.ALL, "crawl_frequency")

    data = payload.model_dump(exclude_unset=True)
    for field_name, value in data.items():
        setattr(website, field_name, value)
    await session.commit()
    await session.refresh(website)

    audit(
        "update",
        resource="website",
        resource_id=str(website.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
        after=data,
    )
    return WebsiteRead.model_validate(website)


@router.delete(
    "/api/websites/{website_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a website (owner/admin)",
)
async def delete_website(
    website_id: uuid.UUID,
    ctx: OrgContext = Depends(require_role("owner", "admin")),
    session: AsyncSession = Depends(get_db),
) -> Response:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    from datetime import datetime, timezone

    # remove the website's chunks from search, then soft-delete
    page_ids = (
        await session.scalars(select(WebsitePage.id).where(WebsitePage.website_id == website.id))
    ).all()
    if page_ids:
        from sqlalchemy import delete as sa_delete

        await session.execute(
            sa_delete(DocumentChunk).where(DocumentChunk.website_page_id.in_(page_ids))
        )
    website.deleted_at = datetime.now(timezone.utc)
    website.status = WebsiteStatus.paused
    await session.commit()

    audit(
        "delete",
        resource="website",
        resource_id=str(website.id),
        organization_id=str(ctx.organization_id),
        user_id=str(ctx.user_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────── crawl control ───────────────────

@router.post("/api/websites/{website_id}/crawl", response_model=CrawlJobRead, summary="Start a crawl")
async def crawl_website(
    website_id: uuid.UUID,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> CrawlJobRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    if website.status == WebsiteStatus.crawling:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A crawl is already running.")
    job = await _start_crawl(session, website, background)
    return CrawlJobRead.model_validate(job)


@router.post("/api/websites/{website_id}/recrawl", response_model=CrawlJobRead, summary="Force re-crawl")
async def recrawl_website(
    website_id: uuid.UUID,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> CrawlJobRead:
    return await crawl_website(website_id, background, ctx, session)


@router.post("/api/websites/{website_id}/pause", response_model=WebsiteRead, summary="Pause a website")
async def pause_website(
    website_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    website.status = WebsiteStatus.paused
    website.next_crawl_at = None
    # Signal any in-flight crawl to stop cooperatively (frontier is preserved
    # so the crawl can be resumed exactly where it left off).
    await session.execute(
        update(CrawlJob)
        .where(CrawlJob.website_id == website.id)
        .where(CrawlJob.status.in_((CrawlJobStatus.queued, CrawlJobStatus.crawling)))
        .values(status=CrawlJobStatus.paused)
    )
    await session.commit()
    await session.refresh(website)
    return WebsiteRead.model_validate(website)


@router.post("/api/websites/{website_id}/resume", response_model=WebsiteRead, summary="Resume a website")
async def resume_website(
    website_id: uuid.UUID,
    background: BackgroundTasks,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    # If a paused job still has un-fetched URLs in its frontier, resume it in
    # place rather than starting a fresh crawl.
    paused_job = await session.scalar(
        select(CrawlJob)
        .where(CrawlJob.website_id == website.id)
        .where(CrawlJob.status == CrawlJobStatus.paused)
        .order_by(CrawlJob.created_at.desc())
    )
    if paused_job is not None:
        pending = await session.scalar(
            select(func.count())
            .select_from(CrawlFrontier)
            .where(CrawlFrontier.job_id == paused_job.id)
            .where(CrawlFrontier.status.in_((FrontierStatus.pending, FrontierStatus.claimed)))
        )
        if pending:
            paused_job.status = CrawlJobStatus.queued
            website.status = WebsiteStatus.crawling
            website.error = None
            await session.commit()
            await session.refresh(website)
            background.add_task(run_crawl, paused_job.id)
            return WebsiteRead.model_validate(website)

    website.status = WebsiteStatus.ready if website.pages_count else WebsiteStatus.pending
    await session.commit()
    await session.refresh(website)
    return WebsiteRead.model_validate(website)


@router.post("/api/websites/{website_id}/cancel", response_model=WebsiteRead, summary="Cancel a running crawl")
async def cancel_website(
    website_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteRead:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    # Stop the active crawl; the engine drains and finalises as cancelled.
    await session.execute(
        update(CrawlJob)
        .where(CrawlJob.website_id == website.id)
        .where(CrawlJob.status.in_((CrawlJobStatus.queued, CrawlJobStatus.crawling, CrawlJobStatus.paused)))
        .values(status=CrawlJobStatus.cancelled)
    )
    website.status = WebsiteStatus.ready if website.pages_count else WebsiteStatus.pending
    await session.commit()
    await session.refresh(website)
    return WebsiteRead.model_validate(website)


# ─────────────────── pages ───────────────────

@router.get(
    "/api/websites/{website_id}/pages",
    response_model=WebsitePageListResponse,
    summary="List crawled pages",
)
async def list_pages(
    website_id: uuid.UUID,
    q: Optional[str] = Query(default=None, max_length=200),
    classification: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsitePageListResponse:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    base = (
        select(WebsitePage)
        .where(WebsitePage.website_id == website.id)
        .where(WebsitePage.status != PageStatus.deleted)
    )
    if q:
        like = f"%{q}%"
        base = base.where(or_(WebsitePage.url.ilike(like), WebsitePage.title.ilike(like)))
    if classification:
        base = base.where(WebsitePage.classification == classification)
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (
        await session.scalars(base.order_by(asc(WebsitePage.depth), asc(WebsitePage.url)).limit(limit).offset(offset))
    ).all()
    return WebsitePageListResponse(
        items=[WebsitePageRead.model_validate(p) for p in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/websites/{website_id}/pages/{page_id}",
    response_model=WebsitePageDetail,
    summary="Get a page (with markdown)",
)
async def get_page(
    website_id: uuid.UUID,
    page_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsitePageDetail:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    page = await session.scalar(
        select(WebsitePage)
        .where(WebsitePage.id == page_id)
        .where(WebsitePage.website_id == website.id)
    )
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page not found.")
    return WebsitePageDetail.model_validate(page)


# ─────────────────── jobs & logs ───────────────────

@router.get(
    "/api/websites/{website_id}/jobs",
    response_model=CrawlJobListResponse,
    summary="List crawl jobs",
)
async def list_jobs(
    website_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> CrawlJobListResponse:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    base = select(CrawlJob).where(CrawlJob.website_id == website.id)
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (
        await session.scalars(base.order_by(desc(CrawlJob.created_at)).limit(limit).offset(offset))
    ).all()
    return CrawlJobListResponse(
        items=[CrawlJobRead.model_validate(j) for j in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/api/websites/{website_id}/jobs/{job_id}/logs",
    response_model=CrawlLogListResponse,
    summary="Crawl logs for a job",
)
async def list_job_logs(
    website_id: uuid.UUID,
    job_id: uuid.UUID,
    level: Optional[str] = Query(default=None, description="info | warn | error"),
    limit: int = Query(default=200, ge=1, le=1000),
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> CrawlLogListResponse:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")
    base = (
        select(CrawlLog)
        .where(CrawlLog.job_id == job_id)
        .where(CrawlLog.website_id == website.id)
    )
    if level:
        base = base.where(CrawlLog.level == level)
    total = int(await session.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = (await session.scalars(base.order_by(asc(CrawlLog.created_at)).limit(limit))).all()
    return CrawlLogListResponse(
        items=[CrawlLogRead.model_validate(x) for x in rows],
        total=total,
    )


# ─────────────────── analytics ───────────────────

@router.get(
    "/api/websites/{website_id}/analytics",
    response_model=WebsiteAnalytics,
    summary="Website coverage analytics",
)
async def website_analytics(
    website_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    session: AsyncSession = Depends(get_db),
) -> WebsiteAnalytics:
    website = await _website_for_org(session, website_id=website_id, organization_id=ctx.organization_id)
    if website is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Website not found.")

    indexed = int(
        await session.scalar(
            select(func.count(WebsitePage.id))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status == PageStatus.crawled)
        )
        or 0
    )
    failed = int(
        await session.scalar(
            select(func.count(WebsitePage.id))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status == PageStatus.failed)
        )
        or 0
    )
    skipped = int(
        await session.scalar(
            select(func.count(WebsitePage.id))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status == PageStatus.skipped)
        )
        or 0
    )
    chunks_total = int(
        await session.scalar(
            select(func.coalesce(func.sum(WebsitePage.chunk_count), 0))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status != PageStatus.deleted)
        )
        or 0
    )
    words_total = int(
        await session.scalar(
            select(func.coalesce(func.sum(WebsitePage.word_count), 0))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status != PageStatus.deleted)
        )
        or 0
    )
    class_rows = (
        await session.execute(
            select(WebsitePage.classification, func.count(WebsitePage.id))
            .where(WebsitePage.website_id == website.id)
            .where(WebsitePage.status != PageStatus.deleted)
            .group_by(WebsitePage.classification)
        )
    ).all()
    by_classification = {(c or "other"): int(n) for c, n in class_rows}

    last_job = await session.scalar(
        select(CrawlJob)
        .where(CrawlJob.website_id == website.id)
        .order_by(desc(CrawlJob.created_at))
        .limit(1)
    )

    return WebsiteAnalytics(
        website_id=website.id,
        status=website.status,
        pages_total=indexed + failed + skipped,
        pages_indexed=indexed,
        pages_failed=failed,
        pages_skipped=skipped,
        chunks_total=chunks_total,
        word_count_total=words_total,
        by_classification=by_classification,
        last_crawled_at=website.last_crawled_at,
        next_crawl_at=website.next_crawl_at,
        last_job=CrawlJobRead.model_validate(last_job) if last_job else None,
    )
