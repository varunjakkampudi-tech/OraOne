"""Leads (CRM) — first-class lead capture and pipeline.

Creates the ``leads`` table so conversations/widgets can materialise sales
leads with status, scoring and assignment (previously leads only existed as
append-only ``widget_events`` of type ``lead``).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0025_leads"
down_revision: Union[str, None] = "0024_projects"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ``create_type=False`` so SQLAlchemy never auto-emits CREATE TYPE during the
# CREATE TABLE that references these — we issue CREATE TYPE explicitly below.
lead_status = postgresql.ENUM(
    "new", "contacted", "qualified", "won", "lost",
    name="lead_status", create_type=False,
)
lead_temperature = postgresql.ENUM(
    "hot", "warm", "cold",
    name="lead_temperature", create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE lead_status AS ENUM "
        "('new', 'contacted', 'qualified', 'won', 'lost')"
    )
    op.execute(
        "CREATE TYPE lead_temperature AS ENUM ('hot', 'warm', 'cold')"
    )

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "widget_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("widgets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(160)),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(40)),
        sa.Column("company", sa.String(200)),
        sa.Column("intent", sa.String(255)),
        sa.Column("message", sa.Text()),
        sa.Column(
            "source", sa.String(40), nullable=False, server_default="widget"
        ),
        sa.Column("status", lead_status, nullable=False, server_default="new"),
        sa.Column(
            "temperature", lead_temperature, nullable=False, server_default="warm"
        ),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "extra",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
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
    )
    op.create_index("ix_leads_organization_id", "leads", ["organization_id"])
    op.create_index("ix_leads_project_id", "leads", ["project_id"])
    op.create_index("ix_leads_status", "leads", ["status"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])
    op.create_index("ix_leads_email", "leads", ["email"])


def downgrade() -> None:
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_status", table_name="leads")
    op.drop_index("ix_leads_project_id", table_name="leads")
    op.drop_index("ix_leads_organization_id", table_name="leads")
    op.drop_table("leads")
    op.execute("DROP TYPE IF EXISTS lead_temperature")
    op.execute("DROP TYPE IF EXISTS lead_status")
