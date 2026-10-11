"""Product catalog — platform-level definition of OraOne's sellable products.

Phase 1 (Entitlements). A *product* is a top-level, independently-licensable
surface of the platform:

    * ``ai_platform``    — OraOne AI Platform (chat, agents, knowledge, workflows)

This table is the **platform-global** source of truth for a product's launch
state (status / visibility / version / release notes). Whether a *specific
organization* may use a product is decided by ``OrganizationEntitlement`` layered
on top of a product's ``default_enabled`` — see
:mod:`app.services.entitlements`.

Status / visibility are stored as short strings (matching the ``operations``
models) rather than native PG enums, so new states can be introduced without a
schema migration. Use the ``ProductStatus`` / ``ProductVisibility`` constant
classes as the single source of truth for valid values.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import Boolean, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ProductStatus:
    """Platform-global launch lifecycle of a product.

    ``USABLE`` is the set of states in which an *entitled* org may actually use
    the product. Everything else is blocked at the API layer (fail-closed):

      * ``coming_soon`` — announced, not yet usable.
      * ``preview``     — early access; usable by entitled orgs.
      * ``beta``        — usable by entitled orgs; UI may show a Beta badge.
      * ``ga``          — general availability (the steady state).
      * ``active``      — legacy alias for ``ga`` (kept for back-compat).
      * ``deprecated``  — sunsetting; still usable, UI should warn.
      * ``maintenance`` — temporarily blocked platform-wide (HTTP 503).
      * ``internal``    — internal/staff only; blocked for customer orgs.
      * ``disabled``    — switched off for everyone (HTTP 403).
    """

    COMING_SOON = "coming_soon"
    PREVIEW = "preview"
    BETA = "beta"
    GA = "ga"
    ACTIVE = "active"  # legacy alias, treated as GA
    DEPRECATED = "deprecated"
    MAINTENANCE = "maintenance"
    INTERNAL = "internal"
    DISABLED = "disabled"

    ALL = (
        COMING_SOON, PREVIEW, BETA, GA, ACTIVE, DEPRECATED,
        MAINTENANCE, INTERNAL, DISABLED,
    )
    #: States in which an entitled org may use the product.
    USABLE = (PREVIEW, BETA, GA, ACTIVE, DEPRECATED)


class ProductVisibility:
    """Whether the product surfaces in navigation / catalogue.

    Visibility is *presentational only* — it controls discovery (nav, command
    palette, marketing), never authorization. A ``hidden`` product an org is
    entitled to still works via a direct link; it just isn't advertised.
    """

    VISIBLE = "visible"
    HIDDEN = "hidden"
    INTERNAL = "internal"
    ALL = (VISIBLE, HIDDEN, INTERNAL)


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A top-level, independently-licensable OraOne product."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("key", name="uq_products_key"),
        UniqueConstraint("slug", name="uq_products_slug"),
        Index("ix_products_status", "status"),
    )

    #: Stable machine key (e.g. ``ai_platform``). Never renamed.
    key: Mapped[str] = mapped_column(String(60), nullable=False)
    #: URL-safe slug (defaults to ``key``); used in routes / deep links.
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    #: Internal name (legacy field, kept populated for back-compat).
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Customer-facing display name.
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    #: Lucide/asset icon identifier for nav + admin rendering.
    icon: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    #: Frontend route prefix the product owns (e.g. ``/app``).
    route_prefix: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    documentation_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=ProductStatus.GA, server_default=ProductStatus.GA,
    )
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False,
        default=ProductVisibility.VISIBLE, server_default=ProductVisibility.VISIBLE,
    )
    version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="1.0.0", server_default="1.0.0",
    )
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    #: Feature keys enabled by default for this product (Product → Feature map).
    default_features: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]",
    )
    #: Default entitlement for organizations without an explicit override row.
    default_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true",
    )
    #: Ordering hint for admin/nav rendering (a.k.a. display order).
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.key} status={self.status}>"
