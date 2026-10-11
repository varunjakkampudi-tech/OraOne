"""AI Marketplace API — Phase Z.

A curated, in-code catalogue (:mod:`app.services.marketplace`) of installable
building blocks: agent templates, integrations and workflows.

* ``GET    /api/marketplace/categories``               — catalogue facets
* ``GET    /api/marketplace/listings``                 — browse/search the catalogue
* ``GET    /api/marketplace/listings/{slug}``          — one listing
* ``POST   /api/marketplace/listings/{slug}/install``  — install into the active project
* ``GET    /api/marketplace/installations``            — what this org has installed
* ``DELETE /api/marketplace/installations/{id}``       — uninstall

Installing an ``agent_template`` provisions a real :class:`Agent` (+ config) in
the active project so the tenant has a working agent immediately.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.agent import Agent, AgentStatus, AgentType
from app.database.models.agent_config import AgentConfig
from app.database.models.knowledge_base import KnowledgeBase, KnowledgeBaseStatus
from app.database.models.marketplace import InstallStatus, MarketplaceInstallation
from app.database.models.marketplace_review import MarketplaceReview
from app.database.models.user import User
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.services import marketplace as catalog
from app.services.audit import audit

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ─────────────────────────────── schemas ─────────────────────────────────────

class ListingRead(BaseModel):
    slug: str
    name: str
    category: str
    summary: str
    icon: str
    tags: list[str]
    author: str
    featured: bool
    installed: bool = False
    rating: float = 0.0
    review_count: int = 0


class ListingDetail(ListingRead):
    blueprint: dict[str, Any]


class ReviewRead(BaseModel):
    id: uuid.UUID
    listing_slug: str
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    author: str
    is_mine: bool = False
    created_at: Any


class ReviewCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(default=None, max_length=160)
    body: Optional[str] = Field(default=None, max_length=4000)


class ReviewListResponse(BaseModel):
    average: float
    count: int
    distribution: dict[int, int]
    my_review: Optional[ReviewRead] = None
    reviews: list[ReviewRead]


class InstallationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    listing_slug: str
    listing_name: str
    category: str
    status: str
    agent_id: Optional[uuid.UUID] = None
    created_at: Any


class InstallResponse(BaseModel):
    installation: InstallationRead
    agent_id: Optional[uuid.UUID] = None


# ─────────────────────────────── helpers ─────────────────────────────────────

async def _installed_slugs(db: AsyncSession, organization_id: uuid.UUID) -> set[str]:
    rows = await db.scalars(
        select(MarketplaceInstallation.listing_slug)
        .where(MarketplaceInstallation.organization_id == organization_id)
        .where(MarketplaceInstallation.status == InstallStatus.installed)
    )
    return set(rows.all())


async def _ratings_for(db: AsyncSession, slugs: Optional[list[str]] = None) -> dict[str, dict[str, Any]]:
    """Aggregate average rating + review count per listing slug (global)."""
    stmt = select(
        MarketplaceReview.listing_slug,
        func.avg(MarketplaceReview.rating),
        func.count(MarketplaceReview.id),
    ).group_by(MarketplaceReview.listing_slug)
    if slugs:
        stmt = stmt.where(MarketplaceReview.listing_slug.in_(slugs))
    rows = (await db.execute(stmt)).all()
    return {
        slug: {"rating": round(float(avg or 0), 1), "review_count": int(cnt or 0)}
        for slug, avg, cnt in rows
    }


def _to_listing_read(
    item: dict[str, Any], installed: set[str],
    ratings: Optional[dict[str, dict[str, Any]]] = None,
) -> ListingRead:
    agg = (ratings or {}).get(item["slug"], {})
    return ListingRead(
        slug=item["slug"],
        name=item["name"],
        category=item["category"],
        summary=item["summary"],
        icon=item["icon"],
        tags=item.get("tags", []),
        author=item["author"],
        featured=bool(item.get("featured")),
        installed=item["slug"] in installed,
        rating=agg.get("rating", 0.0),
        review_count=agg.get("review_count", 0),
    )


# ─────────────────────────────── routes ──────────────────────────────────────

@router.get("/categories")
async def list_categories(
    _ctx: OrgContext = Depends(get_current_organization),
) -> list[dict[str, str]]:
    return catalog.CATEGORIES


@router.get("/listings", response_model=list[ListingRead])
async def list_listings(
    category: Optional[str] = Query(default=None),
    q: Optional[str] = Query(default=None),
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> list[ListingRead]:
    installed = await _installed_slugs(db, ctx.organization_id)
    items = catalog.list_listings(category=category, q=q)
    ratings = await _ratings_for(db, [i["slug"] for i in items])
    return [_to_listing_read(i, installed, ratings) for i in items]


@router.get("/listings/{slug}", response_model=ListingDetail)
async def get_listing(
    slug: str,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ListingDetail:
    item = catalog.get_listing(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    installed = await _installed_slugs(db, ctx.organization_id)
    ratings = await _ratings_for(db, [slug])
    base = _to_listing_read(item, installed, ratings)
    return ListingDetail(**base.model_dump(), blueprint=item.get("blueprint", {}))


@router.get("/installations", response_model=list[InstallationRead])
async def list_installations(
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> list[MarketplaceInstallation]:
    rows = await db.scalars(
        select(MarketplaceInstallation)
        .where(MarketplaceInstallation.organization_id == ctx.organization_id)
        .where(MarketplaceInstallation.status == InstallStatus.installed)
        .order_by(desc(MarketplaceInstallation.created_at))
    )
    return list(rows.all())


@router.post(
    "/listings/{slug}/install",
    response_model=InstallResponse,
    status_code=status.HTTP_201_CREATED,
)
async def install_listing(
    slug: str,
    pctx: ProjectContext = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> InstallResponse:
    item = catalog.get_listing(slug)
    if item is None:
        raise HTTPException(status_code=404, detail="Listing not found.")
    ctx = pctx.org

    # Idempotent: if already installed, return the existing record.
    existing = await db.scalar(
        select(MarketplaceInstallation)
        .where(MarketplaceInstallation.organization_id == ctx.organization_id)
        .where(MarketplaceInstallation.listing_slug == slug)
        .where(MarketplaceInstallation.status == InstallStatus.installed)
    )
    if existing is not None:
        return InstallResponse(
            installation=InstallationRead.model_validate(existing),
            agent_id=existing.agent_id,
        )

    blueprint = item.get("blueprint", {})
    agent_id: Optional[uuid.UUID] = None

    # Agent templates provision a real, ready-to-use Agent in the active project.
    if item["category"] == "agent_template":
        agent = Agent(
            organization_id=ctx.organization_id,
            project_id=pctx.project_id,
            name=item["name"],
            description=item["summary"],
            type=AgentType.chat,
            status=AgentStatus.draft,
            model=blueprint.get("model", "gpt-4o-mini"),
            created_by_user_id=ctx.user_id,
        )
        db.add(agent)
        await db.flush()
        cfg = AgentConfig(
            agent_id=agent.id,
            system_prompt=blueprint.get("system_prompt"),
            temperature=0.70,
            voice=blueprint.get("voice"),
            language=blueprint.get("language", "en"),
            greeting=blueprint.get("greeting"),
            max_tokens=1024,
        )
        db.add(cfg)
        await db.flush()
        agent_id = agent.id

        # Provision a starter knowledge base reflecting the template's structure.
        try:
            topics = blueprint.get("knowledge_structure") or []
            kb = KnowledgeBase(
                organization_id=ctx.organization_id,
                project_id=pctx.project_id,
                name=f"{item['name']} Knowledge",
                description=(
                    "Starter knowledge base. Suggested structure: "
                    + ", ".join(topics)
                    if topics else "Starter knowledge base."
                ),
                status=KnowledgeBaseStatus.draft,
            )
            db.add(kb)
            await db.flush()
            kb_id = str(kb.id)
        except Exception:  # noqa: BLE001 — never block the agent install
            kb_id = None

    row = MarketplaceInstallation(
        organization_id=ctx.organization_id,
        project_id=pctx.project_id,
        installed_by_user_id=ctx.user_id,
        agent_id=agent_id,
        listing_slug=item["slug"],
        listing_name=item["name"],
        category=item["category"],
        status=InstallStatus.installed,
        meta={"blueprint": blueprint, "knowledge_base_id": kb_id if item["category"] == "agent_template" else None},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    audit(
        "install", resource="marketplace_listing", resource_id=item["slug"],
        organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
        meta={"category": item["category"], "agent_id": str(agent_id) if agent_id else None},
    )
    return InstallResponse(
        installation=InstallationRead.model_validate(row),
        agent_id=agent_id,
    )


@router.delete("/installations/{installation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def uninstall_listing(
    installation_id: uuid.UUID,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Response:
    row = await db.scalar(
        select(MarketplaceInstallation)
        .where(MarketplaceInstallation.id == installation_id)
        .where(MarketplaceInstallation.organization_id == ctx.organization_id)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Installation not found.")
    row.status = InstallStatus.removed
    await db.commit()
    audit(
        "uninstall", resource="marketplace_listing", resource_id=row.listing_slug,
        organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ─────────────────────────────── reviews ─────────────────────────────────────

def _author_name(u: Optional[User]) -> str:
    if u is None:
        return "OraOne user"
    name = (getattr(u, "full_name", None) or getattr(u, "name", None) or "").strip()
    return name or (u.email.split("@")[0] if getattr(u, "email", None) else "OraOne user")


def _to_review_read(r: MarketplaceReview, author: str, my_user_id: uuid.UUID) -> ReviewRead:
    return ReviewRead(
        id=r.id,
        listing_slug=r.listing_slug,
        rating=r.rating,
        title=r.title,
        body=r.body,
        author=author,
        is_mine=(r.user_id == my_user_id),
        created_at=r.created_at,
    )


@router.get("/listings/{slug}/reviews", response_model=ReviewListResponse)
async def list_reviews(
    slug: str,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ReviewListResponse:
    if catalog.get_listing(slug) is None:
        raise HTTPException(status_code=404, detail="Listing not found.")

    rows = (
        await db.scalars(
            select(MarketplaceReview)
            .where(MarketplaceReview.listing_slug == slug)
            .order_by(desc(MarketplaceReview.created_at))
            .limit(100)
        )
    ).all()

    user_ids = list({r.user_id for r in rows})
    directory: dict[uuid.UUID, User] = {}
    if user_ids:
        users = (await db.scalars(select(User).where(User.id.in_(user_ids)))).all()
        directory = {u.id: u for u in users}

    distribution = {i: 0 for i in range(1, 6)}
    total = 0
    reviews: list[ReviewRead] = []
    mine: Optional[ReviewRead] = None
    for r in rows:
        distribution[r.rating] = distribution.get(r.rating, 0) + 1
        total += r.rating
        rr = _to_review_read(r, _author_name(directory.get(r.user_id)), ctx.user_id)
        reviews.append(rr)
        if rr.is_mine:
            mine = rr

    count = len(rows)
    average = round(total / count, 1) if count else 0.0
    return ReviewListResponse(
        average=average,
        count=count,
        distribution=distribution,
        my_review=mine,
        reviews=reviews,
    )


@router.put("/listings/{slug}/reviews", response_model=ReviewRead, status_code=status.HTTP_200_OK)
async def upsert_review(
    slug: str,
    payload: ReviewCreate,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> ReviewRead:
    if catalog.get_listing(slug) is None:
        raise HTTPException(status_code=404, detail="Listing not found.")

    row = await db.scalar(
        select(MarketplaceReview)
        .where(MarketplaceReview.organization_id == ctx.organization_id)
        .where(MarketplaceReview.user_id == ctx.user_id)
        .where(MarketplaceReview.listing_slug == slug)
    )
    if row is None:
        row = MarketplaceReview(
            organization_id=ctx.organization_id,
            user_id=ctx.user_id,
            listing_slug=slug,
            rating=payload.rating,
            title=payload.title,
            body=payload.body,
        )
        db.add(row)
        action = "create"
    else:
        row.rating = payload.rating
        row.title = payload.title
        row.body = payload.body
        action = "update"
    await db.commit()
    await db.refresh(row)

    user = await db.get(User, ctx.user_id)
    audit(
        action, resource="marketplace_review", resource_id=slug,
        organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
        meta={"rating": payload.rating},
    )
    return _to_review_read(row, _author_name(user), ctx.user_id)


@router.delete("/listings/{slug}/reviews", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_review(
    slug: str,
    ctx: OrgContext = Depends(get_current_organization),
    db: AsyncSession = Depends(get_db),
) -> Response:
    row = await db.scalar(
        select(MarketplaceReview)
        .where(MarketplaceReview.organization_id == ctx.organization_id)
        .where(MarketplaceReview.user_id == ctx.user_id)
        .where(MarketplaceReview.listing_slug == slug)
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    await db.delete(row)
    await db.commit()
    audit(
        "delete", resource="marketplace_review", resource_id=slug,
        organization_id=str(ctx.organization_id), user_id=str(ctx.user_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
