"""R3 Website Crawling Engine + R4 RAG multi-source chunks.

Creates websites / website_pages / crawl_jobs / crawl_logs and extends
document_chunks so a chunk can belong to a crawled WebsitePage as well as
an uploaded Document, with denormalised org/KB scoping and a full-text
search index for hybrid retrieval.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0020_website_crawling"
down_revision: Union[str, None] = "0019_knowledge_organization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── websites ──
    op.create_table(
        "websites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("crawl_mode", sa.String(length=20), nullable=False, server_default="entire"),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("crawl_frequency", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("respect_robots", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("include_paths", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("exclude_paths", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("allowed_domains", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("auth_config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("pages_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_crawl_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_websites_organization_id", "websites", ["organization_id"], if_not_exists=True)
    op.create_index("ix_websites_knowledge_base_id", "websites", ["knowledge_base_id"], if_not_exists=True)
    op.create_index("ix_websites_status", "websites", ["status"], if_not_exists=True)
    op.create_index("ix_websites_next_crawl_at", "websites", ["next_crawl_at"], if_not_exists=True)

    # ── website_pages ──
    op.create_table(
        "website_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=True),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("checksum", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="crawled"),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=True),
        sa.Column("content_type", sa.String(length=120), nullable=True),
        sa.Column("classification", sa.String(length=40), nullable=True),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_crawled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("page_metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["website_id"], ["websites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("website_id", "url", name="uq_website_pages_site_url"),
        if_not_exists=True,
    )
    op.create_index("ix_website_pages_website_id", "website_pages", ["website_id"], if_not_exists=True)
    op.create_index("ix_website_pages_organization_id", "website_pages", ["organization_id"], if_not_exists=True)
    op.create_index("ix_website_pages_checksum", "website_pages", ["checksum"], if_not_exists=True)
    op.create_index("ix_website_pages_status", "website_pages", ["status"], if_not_exists=True)

    # ── crawl_jobs ──
    op.create_table(
        "crawl_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="queued"),
        sa.Column("trigger", sa.String(length=16), nullable=False, server_default="manual"),
        sa.Column("pages_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pages_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunks_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["website_id"], ["websites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_crawl_jobs_website_id", "crawl_jobs", ["website_id"], if_not_exists=True)
    op.create_index("ix_crawl_jobs_organization_id", "crawl_jobs", ["organization_id"], if_not_exists=True)
    op.create_index("ix_crawl_jobs_status", "crawl_jobs", ["status"], if_not_exists=True)

    # ── crawl_logs ──
    op.create_table(
        "crawl_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("website_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=True),
        sa.Column("level", sa.String(length=10), nullable=False, server_default="info"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["job_id"], ["crawl_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["website_id"], ["websites.id"], ondelete="CASCADE"),
        if_not_exists=True,
    )
    op.create_index("ix_crawl_logs_job_id", "crawl_logs", ["job_id"], if_not_exists=True)
    op.create_index("ix_crawl_logs_website_id", "crawl_logs", ["website_id"], if_not_exists=True)

    # ── document_chunks: multi-source + denormalised scope (R4) ──
    op.add_column("document_chunks", sa.Column("website_page_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("document_chunks", sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("document_chunks", sa.Column("knowledge_base_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_document_chunks_website_page", "document_chunks", "website_pages",
        ["website_page_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_document_chunks_organization", "document_chunks", "organizations",
        ["organization_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_document_chunks_kb", "document_chunks", "knowledge_bases",
        ["knowledge_base_id"], ["id"], ondelete="CASCADE",
    )
    # document_id becomes nullable (website chunks have no document).
    op.alter_column("document_chunks", "document_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)

    # Backfill org/KB onto existing document chunks from their document.
    op.execute(
        """
        UPDATE document_chunks AS dc
        SET organization_id = d.organization_id,
            knowledge_base_id = d.knowledge_base_id
        FROM documents AS d
        WHERE dc.document_id = d.id
          AND dc.organization_id IS NULL
        """
    )

    op.create_index("ix_document_chunks_website_page_id", "document_chunks", ["website_page_id"], if_not_exists=True)
    op.create_index("ix_document_chunks_organization_id", "document_chunks", ["organization_id"], if_not_exists=True)
    op.create_index("ix_document_chunks_knowledge_base_id", "document_chunks", ["knowledge_base_id"], if_not_exists=True)

    # Full-text search index for hybrid retrieval (R4).
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_content_fts "
        "ON document_chunks USING gin (to_tsvector('english', content))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_fts")
    for ix in (
        "ix_document_chunks_knowledge_base_id",
        "ix_document_chunks_organization_id",
        "ix_document_chunks_website_page_id",
    ):
        op.drop_index(ix, table_name="document_chunks", if_exists=True)
    op.drop_constraint("fk_document_chunks_kb", "document_chunks", type_="foreignkey")
    op.drop_constraint("fk_document_chunks_organization", "document_chunks", type_="foreignkey")
    op.drop_constraint("fk_document_chunks_website_page", "document_chunks", type_="foreignkey")
    op.drop_column("document_chunks", "knowledge_base_id")
    op.drop_column("document_chunks", "organization_id")
    op.drop_column("document_chunks", "website_page_id")
    # NB: document_id is left nullable on downgrade (harmless).

    op.drop_table("crawl_logs")
    op.drop_table("crawl_jobs")
    op.drop_table("website_pages")
    op.drop_table("websites")
