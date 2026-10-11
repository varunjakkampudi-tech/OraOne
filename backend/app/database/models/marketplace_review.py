"""MarketplaceReview — tenant ratings & written reviews for catalogue listings.

The marketplace catalogue lives in code (slug-keyed), so a review only needs
to reference the ``listing_slug`` rather than a foreign key. One review per
(organization, user, listing) — re-submitting updates the existing row.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MarketplaceReview(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "marketplace_reviews"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "user_id", "listing_slug",
            name="uq_marketplace_review_org_user_slug",
        ),
        Index("ix_marketplace_reviews_slug", "listing_slug"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    listing_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    title: Mapped[Optional[str]] = mapped_column(String(160))
    body: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MarketplaceReview slug={self.listing_slug} rating={self.rating}>"
