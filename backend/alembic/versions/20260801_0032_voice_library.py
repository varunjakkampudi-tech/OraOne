"""Phase 9 — enterprise voice library.

Adds ``voice_library``: an org-owned catalogue of branded / cloned voices
with an approval lifecycle (pending → approved → revoked) and consent
provenance for governance (Phase 9.3 Custom Voices & Voice Cloning).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0032_voice_library"
down_revision: Union[str, None] = "0031_voice_workflow_triggers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_library",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("slug", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False, server_default="elevenlabs"),
        sa.Column("provider_voice_id", sa.String(length=120), nullable=True),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="custom"),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("gender", sa.String(length=20), nullable=True),
        sa.Column("accent", sa.String(length=40), nullable=True),
        sa.Column("style_profile", sa.String(length=40), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("consent_obtained", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_voice_library_org_slug"),
    )
    op.create_index("ix_voice_library_organization_id", "voice_library", ["organization_id"])
    op.create_index("ix_voice_library_status", "voice_library", ["status"])


def downgrade() -> None:
    op.drop_index("ix_voice_library_status", table_name="voice_library")
    op.drop_index("ix_voice_library_organization_id", table_name="voice_library")
    op.drop_table("voice_library")
