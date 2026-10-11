"""Marketplace ratings & reviews (feature #15).

Adds ``marketplace_reviews`` — one rating/review per (organization, user,
listing_slug). Powers star ratings, review counts and the review feed on
each marketplace listing.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0040_marketplace_reviews"
down_revision: Union[str, None] = "0039_agent_prompt_versions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("listing_slug", sa.String(120), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("title", sa.String(160)),
        sa.Column("body", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id", "user_id", "listing_slug",
            name="uq_marketplace_review_org_user_slug",
        ),
    )
    op.create_index(
        "ix_marketplace_reviews_slug", "marketplace_reviews", ["listing_slug"]
    )


def downgrade() -> None:
    op.drop_index("ix_marketplace_reviews_slug", table_name="marketplace_reviews")
    op.drop_table("marketplace_reviews")
