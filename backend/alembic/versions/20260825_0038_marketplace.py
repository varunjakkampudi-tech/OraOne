"""Phase Z: AI Marketplace installations.

Adds a single tenant-scoped table backing the AI Marketplace
(``marketplace_installations``). The catalogue itself lives in code
(:mod:`app.services.marketplace`); this table only records what a tenant has
installed and (for agent templates) which Agent it provisioned.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0038_marketplace"
down_revision: Union[str, None] = "0037_payments_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketplace_installations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("installed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("listing_slug", sa.String(length=120), nullable=False),
        sa.Column("listing_name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False, server_default="agent_template"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="installed"),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_marketplace_installations_organization_id", "marketplace_installations", ["organization_id"])
    op.create_index("ix_marketplace_installations_listing_slug", "marketplace_installations", ["listing_slug"])


def downgrade() -> None:
    op.drop_index("ix_marketplace_installations_listing_slug", table_name="marketplace_installations")
    op.drop_index("ix_marketplace_installations_organization_id", table_name="marketplace_installations")
    op.drop_table("marketplace_installations")
