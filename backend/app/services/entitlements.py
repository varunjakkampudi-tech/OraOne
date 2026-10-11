"""Entitlement engine — the platform's authorization foundation.

Single source of truth for **what a given organization is allowed to use** at
runtime, resolved through one path so every caller agrees:

    Product catalog  →  per-org override  →  lifecycle status  →  effective access
    Feature flags    →  parent product    →  org override / rollout  →  effective

Design principles (Phase 1.5 hardening):

* **Fail-closed.** An *unknown* product or feature resolves to **denied**, not
  allowed. Only explicitly public routes bypass entitlement. Known catalog
  products that simply have no per-org override fall back to their
  ``default_enabled`` (this is a *known* default, not a fail-open).
* **Lifecycle-aware.** Products move through ``coming_soon → preview → beta →
  ga → deprecated`` plus ``maintenance`` / ``internal`` / ``disabled``. Only
  :data:`ProductStatus.USABLE` states grant access.
* **Cached.** The per-org entitlement snapshot is memoised in-process with a
  short TTL so the hot path (every guarded request) doesn't hit the DB. All
  mutations invalidate the cache.
* **Deterministic rollout.** A percentage rollout enables a stable subset of
  orgs (hash of org id), never flickering per request.

Runtime enforcement:
  * :func:`require_product` — 403 (denied) / 503 (maintenance) / 403 (coming soon).
  * :func:`require_feature` — 403 unless a feature (and its parent product) is on.
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.operations import FeatureFlag
from app.database.models.organization_entitlement import OrganizationEntitlement
from app.database.models.product import Product, ProductStatus, ProductVisibility
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import cache
from app.services import metrics

log = logging.getLogger("app.entitlements")


# --------------------------------------------------------------------------- #
# Default catalog + Product → Feature map                                      #
# --------------------------------------------------------------------------- #
# (key, slug, name, display_name, description, icon, route_prefix, doc_url,
#  version, default_features, default_enabled, sort_order)
_DEFAULT_PRODUCTS: list[dict[str, Any]] = [
    {
        "key": "ai_platform",
        "slug": "ai-platform",
        "name": "OraOne AI Platform",
        "display_name": "AI Platform",
        "description": (
            "Chat & web AI agents, knowledge base (RAG), workflows, "
            "integrations, CRM and analytics."
        ),
        "icon": "Bot",
        "route_prefix": "/app",
        "documentation_url": "https://docs.oraone.in/ai-platform",
        "version": "2.0.0",
        "default_features": [
            "chat_agents", "knowledge_ai", "workflow_builder", "analytics",
            "crm", "lead_scoring", "memory", "marketplace",
        ],
        "default_enabled": True,
        "sort_order": 0,
    },
]

#: Which product each known feature belongs to (Product → Feature hierarchy).
#: A feature is only usable when BOTH its own flag AND its parent product are on.
#: Features not listed here inherit ``ai_platform`` as their parent.
_FEATURE_PARENT: dict[str, str] = {
    "chat_agents": "ai_platform",
    "memory": "ai_platform",
    "lead_scoring": "ai_platform",
    "analytics": "ai_platform",
    "crm": "ai_platform",
    "marketplace": "ai_platform",
    "workflow_builder": "ai_platform",
    "knowledge_ai": "ai_platform",
    "experimental_models": "ai_platform",
    "ab_testing": "ai_platform",
    "beta_features": "ai_platform",
}
_DEFAULT_PARENT_PRODUCT = "ai_platform"


def _feature_parent(feature_name: str) -> str:
    return _FEATURE_PARENT.get(feature_name, _DEFAULT_PARENT_PRODUCT)


# --------------------------------------------------------------------------- #
# TTL cache for per-org snapshots (pluggable backend)                          #
# --------------------------------------------------------------------------- #
# A snapshot is a fully-resolved, JSON-serialisable dict. The hot path
# (``require_product`` on every request) reads from here; a miss recomputes
# from the DB. Storage sits behind :class:`app.services.cache.CacheBackend` so
# the default in-process dict can be swapped for a distributed backend
# (Redis + pub/sub) without touching call sites. Any mutation invalidates
# affected entries.
_CACHE_TTL_SECONDS = 30.0
_cache: cache.CacheBackend = cache.get_cache_backend()


def _cache_get(organization_id: uuid.UUID) -> Optional[dict[str, Any]]:
    key = str(organization_id)
    value = _cache.get(key)
    if value is None:
        return None
    if _cache.native_ttl:
        # Distributed backend owns expiry; the stored value is the snapshot.
        return value
    expires_at, snapshot = value
    if time.monotonic() >= expires_at:
        _cache.delete(key)
        return None
    return snapshot


def _cache_set(organization_id: uuid.UUID, snapshot: dict[str, Any]) -> None:
    key = str(organization_id)
    if _cache.native_ttl:
        _cache.set(key, snapshot, ttl_seconds=_CACHE_TTL_SECONDS)
    else:
        _cache.set(key, (time.monotonic() + _CACHE_TTL_SECONDS, snapshot))


def invalidate_org(organization_id: uuid.UUID | str) -> None:
    """Drop one org's cached snapshot (org-scoped mutations)."""
    _cache.delete(str(organization_id))


def invalidate_all() -> None:
    """Drop every cached snapshot (platform-wide mutations: products, global flags)."""
    _cache.clear()


# --------------------------------------------------------------------------- #
# Product catalog                                                              #
# --------------------------------------------------------------------------- #
async def _seed_missing_products(session: AsyncSession) -> None:
    """Ensure every default product exists (idempotent)."""
    rows = (await session.scalars(select(Product))).all()
    by_key = {p.key: p for p in rows}
    created = False
    for spec in _DEFAULT_PRODUCTS:
        if spec["key"] not in by_key:
            session.add(Product(
                key=spec["key"], slug=spec["slug"], name=spec["name"],
                display_name=spec["display_name"], description=spec["description"],
                icon=spec["icon"], route_prefix=spec["route_prefix"],
                documentation_url=spec["documentation_url"],
                status=ProductStatus.GA, visibility=ProductVisibility.VISIBLE,
                version=spec["version"], default_features=spec["default_features"],
                default_enabled=spec["default_enabled"], sort_order=spec["sort_order"],
            ))
            created = True
    if created:
        try:
            await session.commit()
            invalidate_all()
        except Exception as e:  # pragma: no cover — race with a concurrent seed
            await session.rollback()
            log.warning("product seed commit failed: %s", e)


async def list_products(session: AsyncSession) -> list[Product]:
    """Return the full product catalog, seeding defaults on first use."""
    await _seed_missing_products(session)
    rows = (
        await session.scalars(
            select(Product).order_by(Product.sort_order, Product.key)
        )
    ).all()
    return list(rows)


async def get_product(session: AsyncSession, key: str) -> Optional[Product]:
    return await session.scalar(select(Product).where(Product.key == key))


def product_to_dict(p: Product) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "key": p.key,
        "slug": p.slug,
        "name": p.name,
        "display_name": p.display_name,
        "description": p.description or "",
        "icon": p.icon,
        "route_prefix": p.route_prefix,
        "documentation_url": p.documentation_url,
        "status": p.status,
        "visibility": p.visibility,
        "version": p.version,
        "release_notes": p.release_notes or "",
        "default_features": list(p.default_features or []),
        "default_enabled": bool(p.default_enabled),
        "sort_order": int(p.sort_order),
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


async def set_product(
    session: AsyncSession, key: str, *,
    status: Optional[str] = None,
    visibility: Optional[str] = None,
    version: Optional[str] = None,
    release_notes: Optional[str] = None,
    default_enabled: Optional[bool] = None,
    display_name: Optional[str] = None,
    description: Optional[str] = None,
    icon: Optional[str] = None,
    documentation_url: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Update a product's platform-level launch state.

    Returns a dict ``{"before": {...}, "after": {...}}`` for audit diffing, or
    ``None`` if the product key is unknown.
    """
    await _seed_missing_products(session)
    product = await get_product(session, key)
    if product is None:
        return None

    before = product_to_dict(product)

    if status is not None:
        if status not in ProductStatus.ALL:
            raise HTTPException(
                status_code=_HTTP.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status '{status}'. Allowed: {list(ProductStatus.ALL)}",
            )
        product.status = status
    if visibility is not None:
        if visibility not in ProductVisibility.ALL:
            raise HTTPException(
                status_code=_HTTP.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Invalid visibility '{visibility}'. "
                    f"Allowed: {list(ProductVisibility.ALL)}"
                ),
            )
        product.visibility = visibility
    if version is not None:
        product.version = version.strip()[:40] or product.version
    if release_notes is not None:
        product.release_notes = release_notes
    if default_enabled is not None:
        product.default_enabled = bool(default_enabled)
    if display_name is not None:
        product.display_name = display_name.strip()[:160] or product.display_name
    if description is not None:
        product.description = description[:500]
    if icon is not None:
        product.icon = icon.strip()[:60] or None
    if documentation_url is not None:
        product.documentation_url = documentation_url.strip()[:500] or None
    if sort_order is not None:
        product.sort_order = int(sort_order)

    await session.commit()
    await session.refresh(product)
    # A product change affects every org's snapshot.
    invalidate_all()
    return {"before": before, "after": product_to_dict(product)}


# --------------------------------------------------------------------------- #
# Effective resolution (pure functions — unit-testable, no DB)                 #
# --------------------------------------------------------------------------- #
def status_is_usable(status_value: str) -> bool:
    """Whether a product in this lifecycle status may be used by an entitled org."""
    return status_value in ProductStatus.USABLE


def _effective_product_enabled(
    status_value: str, default_enabled: bool, override_enabled: Optional[bool]
) -> bool:
    """Resolve whether a product is usable for an org.

    Access requires a *usable* lifecycle status AND the org switch (explicit
    override if present, else the product default). Visibility is presentational
    only and never gates access. ``maintenance`` / ``coming_soon`` / ``disabled``
    / ``internal`` are non-usable statuses ⇒ denied.
    """
    if not status_is_usable(status_value):
        return False
    if override_enabled is not None:
        return bool(override_enabled)
    return bool(default_enabled)


# --------------------------------------------------------------------------- #
# Per-org entitlement resolution                                               #
# --------------------------------------------------------------------------- #
async def _load_overrides(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict[str, OrganizationEntitlement]:
    rows = (
        await session.scalars(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization_id
            )
        )
    ).all()
    return {r.product_key: r for r in rows}


async def get_org_products(
    session: AsyncSession, organization_id: uuid.UUID
) -> list[dict[str, Any]]:
    """Detailed per-product entitlement view for one org (admin + self-service)."""
    products = await list_products(session)
    overrides = await _load_overrides(session, organization_id)
    out: list[dict[str, Any]] = []
    for p in products:
        ov = overrides.get(p.key)
        override_enabled = bool(ov.enabled) if ov is not None else None
        enabled = _effective_product_enabled(p.status, p.default_enabled, override_enabled)
        out.append({
            **product_to_dict(p),
            "enabled": enabled,
            "has_override": ov is not None,
            "override_enabled": override_enabled,
            "maintenance": p.status == ProductStatus.MAINTENANCE,
            "coming_soon": p.status == ProductStatus.COMING_SOON,
            "beta": p.status == ProductStatus.BETA,
            "preview": p.status == ProductStatus.PREVIEW,
            "deprecated": p.status == ProductStatus.DEPRECATED,
        })
    return out


async def set_org_entitlement(
    session: AsyncSession, organization_id: uuid.UUID, product_key: str,
    enabled: bool, *, admin_user_id: Optional[uuid.UUID] = None,
) -> dict[str, Any]:
    """Create or update an org's explicit override for a product.

    Returns ``{"before": {...}|None, "after": {...}}`` for audit diffing.
    """
    row = await session.scalar(
        select(OrganizationEntitlement).where(
            OrganizationEntitlement.organization_id == organization_id,
            OrganizationEntitlement.product_key == product_key,
        )
    )
    before = (
        {"product_key": row.product_key, "enabled": bool(row.enabled)}
        if row is not None else None
    )
    if row is None:
        row = OrganizationEntitlement(
            organization_id=organization_id, product_key=product_key,
            enabled=bool(enabled), updated_by_user_id=admin_user_id,
        )
        session.add(row)
    else:
        row.enabled = bool(enabled)
        row.updated_by_user_id = admin_user_id
    await session.commit()
    await session.refresh(row)
    invalidate_org(organization_id)
    after = {"product_key": row.product_key, "enabled": bool(row.enabled)}
    return {
        "organization_id": str(row.organization_id),
        "product_key": row.product_key,
        "enabled": bool(row.enabled),
        "before": before,
        "after": after,
    }


# --------------------------------------------------------------------------- #
# Analytics — cross-org adoption overview (platform admin)                     #
# --------------------------------------------------------------------------- #
async def entitlement_overview(session: AsyncSession) -> dict[str, Any]:
    """Per-product adoption counts across every organization.

    For each product, an org is *effectively enabled* when it has an explicit
    ``enabled`` override, or (having no override) the product's ``default_enabled``
    is set AND its status is usable. Non-usable statuses (maintenance / disabled /
    coming_soon / internal) count every org as disabled.
    """
    from app.database.models.organization import Organization

    products = await list_products(session)
    total_orgs = int(
        await session.scalar(
            select(func.count()).select_from(Organization).where(
                Organization.deleted_at.is_(None)
            )
        ) or 0
    )

    # override counts per product_key
    override_rows = (
        await session.execute(
            select(
                OrganizationEntitlement.product_key,
                OrganizationEntitlement.enabled,
                func.count().label("n"),
            ).group_by(
                OrganizationEntitlement.product_key,
                OrganizationEntitlement.enabled,
            )
        )
    ).all()
    ov_enabled: dict[str, int] = {}
    ov_disabled: dict[str, int] = {}
    for product_key, enabled, n in override_rows:
        (ov_enabled if enabled else ov_disabled)[product_key] = int(n)

    items: list[dict[str, Any]] = []
    for p in products:
        oe = ov_enabled.get(p.key, 0)
        od = ov_disabled.get(p.key, 0)
        overrides_total = oe + od
        orgs_without_override = max(total_orgs - overrides_total, 0)
        default_on = status_is_usable(p.status) and bool(p.default_enabled)
        effective_enabled = oe + (orgs_without_override if default_on else 0)
        effective_enabled = min(effective_enabled, total_orgs)
        items.append({
            "key": p.key,
            "name": p.display_name or p.name,
            "status": p.status,
            "version": p.version,
            "default_enabled": bool(p.default_enabled),
            "total_orgs": total_orgs,
            "enabled_orgs": effective_enabled,
            "disabled_orgs": max(total_orgs - effective_enabled, 0),
            "overrides": overrides_total,
            "overrides_enabled": oe,
            "overrides_disabled": od,
        })
    return {"total_orgs": total_orgs, "products": items}


# --------------------------------------------------------------------------- #
# Feature-flag resolution (Product → Feature)                                  #
# --------------------------------------------------------------------------- #
def _rollout_bucket(organization_id: uuid.UUID, flag_name: str) -> int:
    """Deterministic 0–99 bucket for an (org, flag) pair."""
    digest = hashlib.sha256(f"{organization_id}:{flag_name}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


def _flag_enabled_for_org(flag: FeatureFlag, organization_id: uuid.UUID) -> bool:
    if not flag.enabled:
        return False
    pct = flag.rollout_percentage if flag.rollout_percentage is not None else 100
    if pct >= 100:
        return True
    if pct <= 0:
        return False
    return _rollout_bucket(organization_id, flag.name) < pct


async def _resolve_raw_features(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict[str, bool]:
    """Resolve feature flags WITHOUT the parent-product gate.

    Precedence: an org-scoped flag row overrides the global flag of the same
    name. Global flags are subject to rollout; explicit org rows are absolute.
    """
    rows = (
        await session.scalars(
            select(FeatureFlag).where(
                (FeatureFlag.organization_id.is_(None))
                | (FeatureFlag.organization_id == organization_id)
            )
        )
    ).all()

    global_flags: dict[str, FeatureFlag] = {}
    org_flags: dict[str, FeatureFlag] = {}
    for f in rows:
        (org_flags if f.organization_id is not None else global_flags)[f.name] = f

    resolved: dict[str, bool] = {}
    for name, f in global_flags.items():
        resolved[name] = _flag_enabled_for_org(f, organization_id)
    for name, f in org_flags.items():
        resolved[name] = bool(f.enabled)  # explicit org override, rollout ignored
    return resolved


async def evaluate_features(
    session: AsyncSession, organization_id: uuid.UUID,
    product_enabled: Optional[dict[str, bool]] = None,
) -> dict[str, bool]:
    """Resolve every known feature flag for one org, gated by parent product.

    A feature is enabled only when its own flag is on AND its parent product is
    usable for the org. If ``product_enabled`` (a ``{key: bool}`` map) isn't
    supplied it's computed from the catalog.
    """
    raw = await _resolve_raw_features(session, organization_id)
    if product_enabled is None:
        product_enabled = {
            p["key"]: p["enabled"] for p in await get_org_products(session, organization_id)
        }
    gated: dict[str, bool] = {}
    for name, on in raw.items():
        parent = _feature_parent(name)
        # If the parent product exists in the catalog and is disabled, the
        # feature is off regardless of its own flag. Unknown parent ⇒ treat as
        # enabled parent (feature stands alone).
        parent_ok = product_enabled.get(parent, True)
        gated[name] = bool(on and parent_ok)
    return gated


async def is_feature_enabled(
    session: AsyncSession, organization_id: uuid.UUID, feature_name: str
) -> bool:
    """Whether a single feature is on for an org (fail-closed on unknown)."""
    snapshot = await get_cached_snapshot(session, organization_id)
    features = snapshot.get("features", {})
    if feature_name in features:
        return bool(features[feature_name])
    # Fail-closed: a feature with no flag row and not in the known catalogue is
    # denied rather than silently allowed.
    return False


# --------------------------------------------------------------------------- #
# Snapshot (single resolution path) + cache                                    #
# --------------------------------------------------------------------------- #
async def _build_snapshot(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict[str, Any]:
    detailed = await get_org_products(session, organization_id)
    products = {p["key"]: p["enabled"] for p in detailed}
    maintenance = {p["key"]: p["maintenance"] for p in detailed}
    statuses = {p["key"]: p["status"] for p in detailed}
    features = await evaluate_features(session, organization_id, product_enabled=products)
    return {
        "products": products,
        "maintenance": maintenance,
        "statuses": statuses,
        "features": features,
        "catalog": [
            {
                "key": p["key"],
                "slug": p["slug"],
                "name": p["display_name"] or p["name"],
                "description": p["description"],
                "icon": p["icon"],
                "route_prefix": p["route_prefix"],
                "documentation_url": p["documentation_url"],
                "version": p["version"],
                "status": p["status"],
                "visibility": p["visibility"],
                "enabled": p["enabled"],
                "maintenance": p["maintenance"],
                "coming_soon": p["coming_soon"],
                "beta": p["beta"],
                "preview": p["preview"],
                "deprecated": p["deprecated"],
            }
            for p in detailed
        ],
    }


async def get_cached_snapshot(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict[str, Any]:
    """Return the org's entitlement snapshot, served from the TTL cache."""
    cached = _cache_get(organization_id)
    if cached is not None:
        metrics.inc("entitlement_cache_hits_total")
        return cached
    metrics.inc("entitlement_cache_misses_total")
    snapshot = await _build_snapshot(session, organization_id)
    _cache_set(organization_id, snapshot)
    return snapshot


async def entitlements_snapshot(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict[str, Any]:
    """Public snapshot for the frontend (cached)."""
    return await get_cached_snapshot(session, organization_id)


async def is_product_enabled(
    session: AsyncSession, organization_id: uuid.UUID, product_key: str
) -> bool:
    """Whether ``organization_id`` may use ``product_key`` right now.

    **Fail-closed:** an unknown product key (not in the catalog) resolves to
    ``False``. Known catalog products fall back to their ``default_enabled``.
    """
    snapshot = await get_cached_snapshot(session, organization_id)
    products = snapshot.get("products", {})
    if product_key not in products:
        return False
    return bool(products[product_key])


async def is_product_in_maintenance(
    session: AsyncSession, organization_id: uuid.UUID, product_key: str
) -> bool:
    snapshot = await get_cached_snapshot(session, organization_id)
    return bool(snapshot.get("maintenance", {}).get(product_key, False))


def _product_status_from_snapshot(snapshot: dict[str, Any], product_key: str) -> Optional[str]:
    return snapshot.get("statuses", {}).get(product_key)


# --------------------------------------------------------------------------- #
# Access-request records (for the "Request Access" CTA)                         #
# --------------------------------------------------------------------------- #
async def record_access_request(
    session: AsyncSession, ctx: OrgContext, product_key: str,
    *, reason: Optional[str] = None,
) -> dict[str, Any]:
    """Persist an audit trail for a customer requesting a product.

    Kept intentionally lightweight — it emits an audit record (see the caller)
    and returns a confirmation payload. No new table is introduced.
    """
    return {
        "product_key": product_key,
        "organization_id": str(ctx.organization_id),
        "user_id": str(ctx.user_id),
        "reason": (reason or "").strip()[:500] or None,
        "status": "received",
    }


# --------------------------------------------------------------------------- #
# FastAPI dependency guards                                                    #
# --------------------------------------------------------------------------- #
_HTTP = status  # alias so ``status`` param names in helpers don't shadow it


def require_product(product_key: str):
    """Dependency factory: block a route unless the caller's org may use
    ``product_key`` (fail-closed).

    Thin wrapper that routes through the unified :mod:`app.services.authorization`
    pipeline, so product, feature, subscription, RBAC and quota checks all share
    one code path. ``503`` for maintenance, ``403`` for coming-soon / disabled /
    not-entitled.

    Attach to *authenticated* routers only — it resolves the org from
    :func:`get_current_organization`, so it must never guard unauthenticated
    webhooks (e.g. Twilio callbacks / media streams).
    """

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        # Lazy import avoids a circular import (authorization imports this module).
        from app.services import authorization as authz

        decision = await authz.authorize(session, ctx, product=product_key)
        decision.raise_for_denied()
        return ctx

    return _checker


def require_feature(feature_name: str):
    """Dependency factory: block a route unless ``feature_name`` (and its parent
    product) is enabled for the caller's org (fail-closed).

    Routes through the unified authorization pipeline (see :func:`require_product`).
    """

    async def _checker(
        ctx: OrgContext = Depends(get_current_organization),
        session: AsyncSession = Depends(get_db),
    ) -> OrgContext:
        from app.services import authorization as authz

        decision = await authz.authorize(session, ctx, feature=feature_name)
        decision.raise_for_denied()
        return ctx

    return _checker
