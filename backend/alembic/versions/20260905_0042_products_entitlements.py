"""Phase 1 — Product catalog & per-org entitlements.

Adds two tables:

* ``products`` — platform-global catalog of licensable OraOne products, with
  launch state (status / visibility / version / release notes) and a
  ``default_enabled`` fallback.
* ``organization_entitlements`` — explicit per-org overrides of a product's
  default entitlement.

Seeds the two launch products: ``ai_platform`` and ``voice_platform``.
"""
from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0042_products_entitlements"
down_revision: Union[str, None] = "0041_voice_suppression"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    products = op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(60), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(160), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("icon", sa.String(60), nullable=True),
        sa.Column("route_prefix", sa.String(120), nullable=True),
        sa.Column("documentation_url", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ga"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="visible"),
        sa.Column("version", sa.String(40), nullable=False, server_default="1.0.0"),
        sa.Column("release_notes", sa.Text(), nullable=True),
        sa.Column("default_features", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("default_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("key", name="uq_products_key"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_index("ix_products_status", "products", ["status"])

    op.create_table(
        "organization_entitlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("product_key", sa.String(60), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "updated_by_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "organization_id", "product_key",
            name="uq_org_entitlements_org_product",
        ),
    )
    op.create_index(
        "ix_org_entitlements_organization_id",
        "organization_entitlements", ["organization_id"],
    )
    op.create_index(
        "ix_org_entitlements_product_key",
        "organization_entitlements", ["product_key"],
    )

    # Seed the two launch products (idempotent-safe: table is freshly created).
    op.bulk_insert(
        products,
        [
            {
                "id": uuid.uuid4(),
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
                "status": "ga",
                "visibility": "visible",
                "version": "2.0.0",
                "release_notes": None,
                "default_features": (
                    '["chat_agents", "knowledge_ai", "workflow_builder", '
                    '"analytics", "crm", "lead_scoring", "memory", "marketplace"]'
                ),
                "default_enabled": True,
                "sort_order": 0,
            },
            {
                "id": uuid.uuid4(),
                "key": "voice_platform",
                "slug": "voice-platform",
                "name": "OraOne Voice Platform",
                "display_name": "Voice Platform",
                "description": (
                    "Inbound & outbound AI voice calling: receptionist, sales & "
                    "support agents, campaigns, compliance and analytics."
                ),
                "icon": "Phone",
                "route_prefix": "/app/voice",
                "documentation_url": "https://docs.oraone.in/voice-platform",
                "status": "ga",
                "visibility": "visible",
                "version": "1.0.0",
                "release_notes": None,
                "default_features": '["voice_agents"]',
                "default_enabled": True,
                "sort_order": 1,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_org_entitlements_product_key", table_name="organization_entitlements"
    )
    op.drop_index(
        "ix_org_entitlements_organization_id", table_name="organization_entitlements"
    )
    op.drop_table("organization_entitlements")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_table("products")
