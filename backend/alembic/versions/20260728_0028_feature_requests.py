"""Feature requests / feedback board.

Adds the ``feature_requests`` table backing the in-product feedback board where
customers submit ideas, report bugs and upvote what matters to them.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0028_feature_requests"
down_revision: Union[str, None] = "0027_distributed_crawler"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_name", sa.String(length=160), nullable=True),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="feature"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("votes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("voter_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_feature_requests_org", "feature_requests", ["organization_id"])
    op.create_index("ix_feature_requests_status", "feature_requests", ["status"])
    op.create_index("ix_feature_requests_type", "feature_requests", ["type"])


def downgrade() -> None:
    op.drop_index("ix_feature_requests_type", table_name="feature_requests")
    op.drop_index("ix_feature_requests_status", table_name="feature_requests")
    op.drop_index("ix_feature_requests_org", table_name="feature_requests")
    op.drop_table("feature_requests")
