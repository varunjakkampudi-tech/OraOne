"""R2 Enterprise Knowledge: knowledge folders, document versions, enrichment cols."""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0019_knowledge_organization"
down_revision: Union[str, None] = "0018_chat_organization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── knowledge_folders ──
    op.create_table(
        "knowledge_folders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_folder_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("color", sa.String(length=9), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index("ix_knowledge_folders_kb", "knowledge_folders", ["knowledge_base_id"], if_not_exists=True)
    op.create_index("ix_knowledge_folders_org", "knowledge_folders", ["organization_id"], if_not_exists=True)
    op.create_index("ix_knowledge_folders_parent", "knowledge_folders", ["parent_folder_id"], if_not_exists=True)

    # ── document_versions ──
    op.create_table(
        "document_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("s3_key", sa.String(length=500), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index("ix_document_versions_document", "document_versions", ["document_id"], if_not_exists=True)
    op.create_index("ix_document_versions_checksum", "document_versions", ["checksum"], if_not_exists=True)

    # ── documents: enrichment & organization columns ──
    op.add_column("documents", sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("checksum", sa.String(length=64), nullable=True))
    op.add_column("documents", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("documents", sa.Column("summary", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("suggested_questions", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("documents", sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"))
    op.add_column("documents", sa.Column("doc_metadata", postgresql.JSONB(), nullable=False, server_default="{}"))
    op.create_index("ix_documents_folder_id", "documents", ["folder_id"], if_not_exists=True)
    op.create_index("ix_documents_checksum", "documents", ["checksum"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_documents_checksum", table_name="documents")
    op.drop_index("ix_documents_folder_id", table_name="documents")
    for col in ("doc_metadata", "tags", "suggested_questions", "summary", "version", "checksum", "folder_id"):
        op.drop_column("documents", col)
    op.drop_table("document_versions")
    op.drop_table("knowledge_folders")
