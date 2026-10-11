"""Per-organization product entitlement (Phase 1).

An entitlement row is an **explicit override** of a product's platform-level
``default_enabled`` for one organization. If no row exists for an
(organization, product) pair, the product's ``default_enabled`` applies.

    effective = product.status == "active"
                and product.visibility == "visible"
                and (entitlement.enabled if row exists else product.default_enabled)

Entitlements are written only by platform administrators (Super Admin Control
Center). Customers can read their own effective entitlements via
``GET /api/entitlements/me`` but can never grant themselves access.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationEntitlement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_entitlements"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "product_key",
            name="uq_org_entitlements_org_product",
        ),
        Index("ix_org_entitlements_organization_id", "organization_id"),
        Index("ix_org_entitlements_product_key", "product_key"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: References ``products.key`` (a stable string, not the UUID PK).
    product_key: Mapped[str] = mapped_column(String(60), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)

    updated_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<OrganizationEntitlement org={self.organization_id} "
            f"product={self.product_key} enabled={self.enabled}>"
        )
