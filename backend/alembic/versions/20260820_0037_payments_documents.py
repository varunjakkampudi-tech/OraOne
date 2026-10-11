"""Phase V & W: payment requests + customer documents.

Adds two tenant-scoped tables backing the AI Payment Assistant
(``voice_payment_requests``) and the AI Document Assistant
(``voice_customer_documents``). Both are plain JSONB-augmented tables with no
new enum types (status/kind are stored as short strings).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0037_payments_documents"
down_revision: Union[str, None] = "0036_omnichannel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_payment_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("voice_calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("customer_email", sa.String(length=254), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="usd"),
        sa.Column("provider", sa.String(length=20), nullable=False, server_default="stripe"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("reference", sa.String(length=120), nullable=True),
        sa.Column("link_url", sa.String(length=1000), nullable=True),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_voice_payment_requests_organization_id", "voice_payment_requests", ["organization_id"])
    op.create_index("ix_voice_payment_requests_project_id", "voice_payment_requests", ["project_id"])
    op.create_index("ix_voice_payment_requests_status", "voice_payment_requests", ["status"])

    op.create_table(
        "voice_customer_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("call_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("voice_calls.id", ondelete="SET NULL"), nullable=True),
        sa.Column("customer_name", sa.String(length=200), nullable=True),
        sa.Column("customer_phone", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=40), nullable=False, server_default="other"),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("storage_key", sa.String(length=1000), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("extracted_fields", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("synced_to_crm", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_voice_customer_documents_organization_id", "voice_customer_documents", ["organization_id"])
    op.create_index("ix_voice_customer_documents_project_id", "voice_customer_documents", ["project_id"])
    op.create_index("ix_voice_customer_documents_status", "voice_customer_documents", ["status"])
    op.create_index("ix_voice_customer_documents_kind", "voice_customer_documents", ["kind"])


def downgrade() -> None:
    op.drop_table("voice_customer_documents")
    op.drop_table("voice_payment_requests")
