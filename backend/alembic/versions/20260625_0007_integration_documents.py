"""Integration documents manifest (Phase 10 — selective sync).

Adds ``integration_documents`` so each integration tracks exactly which
folders/files the user selected to sync, plus per-file sync state
(status, checksum, last_synced) for incremental sync and the
"Synced Items" management UI.

Idempotent: uses ``IF NOT EXISTS`` so it tolerates partial state.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0007_integration_documents"
down_revision: Union[str, None] = "0006_integrations_platform"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "integration_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=160), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("parent_external_id", sa.String(length=255), nullable=True),
        sa.Column("is_folder", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("checksum", sa.String(length=80), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("external_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_synced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["integration_id"], ["integrations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"], ["documents.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "integration_id", "external_id", name="uq_integration_documents_ext"
        ),
        if_not_exists=True,
    )
    op.create_index(
        "ix_integration_documents_integration_id",
        "integration_documents",
        ["integration_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_integration_documents_organization_id",
        "integration_documents",
        ["organization_id"],
        if_not_exists=True,
    )
    op.create_index(
        "ix_integration_documents_selected",
        "integration_documents",
        ["integration_id", "selected"],
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_integration_documents_selected",
        table_name="integration_documents",
        if_exists=True,
    )
    op.drop_index(
        "ix_integration_documents_organization_id",
        table_name="integration_documents",
        if_exists=True,
    )
    op.drop_index(
        "ix_integration_documents_integration_id",
        table_name="integration_documents",
        if_exists=True,
    )
    op.drop_table("integration_documents", if_exists=True)
