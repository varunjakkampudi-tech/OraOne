"""Integrations platform (Phase 10).

Extends ``integrations`` with OAuth/credential + scheduling columns,
adds document provenance columns to ``documents``, and creates the
``sync_jobs`` / ``sync_logs`` tables.

Idempotent guards (``IF NOT EXISTS`` / ``checkfirst``) so the migration
tolerates partially-applied state on shared dev databases.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0006_integrations_platform"
down_revision: Union[str, None] = "0005_rag_embeddings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ``create_type=False`` so SQLAlchemy never auto-emits CREATE TYPE during
# ``op.create_table`` (we create each type explicitly + idempotently below).
connection_type = postgresql.ENUM(
    "oauth", "api_key", "mock", name="integration_connection_type", create_type=False
)
sync_schedule = postgresql.ENUM(
    "manual", "hourly", "daily", "weekly", name="integration_sync_schedule", create_type=False
)
sync_job_status = postgresql.ENUM(
    "queued", "running", "completed", "failed", name="sync_job_status", create_type=False
)
sync_trigger = postgresql.ENUM(
    "manual", "scheduled", "oauth", name="sync_trigger", create_type=False
)
sync_log_level = postgresql.ENUM(
    "info", "warning", "error", name="sync_log_level", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()

    # ── New enum types ──
    for enum_t in (connection_type, sync_schedule, sync_job_status, sync_trigger, sync_log_level):
        enum_t.create(bind, checkfirst=True)

    # ── Extend integration_status with 'syncing' ──
    op.execute("ALTER TYPE integration_status ADD VALUE IF NOT EXISTS 'syncing'")

    # ── integrations: new columns ──
    op.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS category VARCHAR(40)")
    op.execute(
        "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS connection_type "
        "integration_connection_type NOT NULL DEFAULT 'oauth'"
    )
    op.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS access_token TEXT")
    op.execute("ALTER TABLE integrations ADD COLUMN IF NOT EXISTS refresh_token TEXT")
    op.execute(
        "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS external_account VARCHAR(255)"
    )
    op.execute(
        "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS knowledge_base_id UUID"
    )
    op.execute(
        "ALTER TABLE integrations ADD COLUMN IF NOT EXISTS sync_schedule "
        "integration_sync_schedule NOT NULL DEFAULT 'manual'"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_integrations_kb') THEN "
        "ALTER TABLE integrations ADD CONSTRAINT fk_integrations_kb "
        "FOREIGN KEY (knowledge_base_id) REFERENCES knowledge_bases(id) ON DELETE SET NULL; "
        "END IF; END $$;"
    )

    # ── documents: provenance columns ──
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source VARCHAR(40) "
        "NOT NULL DEFAULT 'upload'"
    )
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS integration_id UUID")
    op.execute("ALTER TABLE documents ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)")
    op.execute(
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS external_modified_at TIMESTAMPTZ"
    )
    op.execute(
        "DO $$ BEGIN "
        "IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname='fk_documents_integration') THEN "
        "ALTER TABLE documents ADD CONSTRAINT fk_documents_integration "
        "FOREIGN KEY (integration_id) REFERENCES integrations(id) ON DELETE CASCADE; "
        "END IF; END $$;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_documents_integration_external "
        "ON documents (integration_id, external_id)"
    )

    # ── sync_jobs ──
    op.create_table(
        "sync_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status", sync_job_status, nullable=False, server_default="queued"
        ),
        sa.Column("trigger", sync_trigger, nullable=False, server_default="manual"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("documents_synced", sa.Integer, nullable=False, server_default="0"),
        sa.Column("documents_deleted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(2000)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sync_jobs_integration_id", "sync_jobs", ["integration_id"])
    op.create_index("ix_sync_jobs_organization_id", "sync_jobs", ["organization_id"])
    op.create_index("ix_sync_jobs_status", "sync_jobs", ["status"])

    # ── sync_logs ──
    op.create_table(
        "sync_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sync_jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "integration_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("integrations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event", sa.String(80), nullable=False),
        sa.Column("level", sync_log_level, nullable=False, server_default="info"),
        sa.Column("message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_sync_logs_job_id", "sync_logs", ["job_id"])
    op.create_index("ix_sync_logs_integration_id", "sync_logs", ["integration_id"])
    op.create_index("ix_sync_logs_organization_id", "sync_logs", ["organization_id"])


def downgrade() -> None:
    op.drop_table("sync_logs")
    op.drop_table("sync_jobs")

    op.execute("DROP INDEX IF EXISTS ix_documents_integration_external")
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS fk_documents_integration")
    for col in ("external_modified_at", "external_id", "integration_id", "source"):
        op.execute(f"ALTER TABLE documents DROP COLUMN IF EXISTS {col}")

    op.execute("ALTER TABLE integrations DROP CONSTRAINT IF EXISTS fk_integrations_kb")
    for col in (
        "sync_schedule", "knowledge_base_id", "external_account",
        "token_expires_at", "refresh_token", "access_token",
        "connection_type", "category",
    ):
        op.execute(f"ALTER TABLE integrations DROP COLUMN IF EXISTS {col}")

    for enum_t in (sync_log_level, sync_trigger, sync_job_status, sync_schedule, connection_type):
        enum_t.drop(op.get_bind(), checkfirst=True)
    # Note: the 'syncing' value added to integration_status is left in place
    # (PostgreSQL cannot drop a single enum value without recreating the type).
