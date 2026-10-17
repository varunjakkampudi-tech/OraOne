"""Marketing campaigns: email, SMS and WhatsApp sends to a chosen lead list.

Revision ID: 0058_marketing_campaigns
Revises: 0057_channel_inbound_receipts

Adds ``marketing_campaigns`` (one message, one channel, one status) and
``marketing_recipients`` (one row per lead: queued, sent, skipped or failed, with the
plain-language reason). Downgrade drops both tables and every recipient record.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0058_marketing_campaigns"
down_revision: Union[str, Sequence[str], None] = "0057_channel_inbound_receipts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "marketing_campaigns",
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
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint(
            "channel IN ('email', 'sms', 'whatsapp')",
            name="ck_marketing_campaigns_channel",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'scheduled', 'sending', 'completed', 'cancelled')",
            name="ck_marketing_campaigns_status",
        ),
    )
    op.create_index(
        "ix_marketing_campaigns_organization_id",
        "marketing_campaigns",
        ["organization_id"],
    )
    op.create_index(
        "ix_marketing_campaigns_project_id", "marketing_campaigns", ["project_id"]
    )

    op.create_table(
        "marketing_recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("marketing_campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("skip_reason", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'skipped', 'failed')",
            name="ck_marketing_recipients_status",
        ),
    )
    op.create_index(
        "ix_marketing_recipients_organization_id",
        "marketing_recipients",
        ["organization_id"],
    )
    op.create_index(
        "ix_marketing_recipients_campaign_status",
        "marketing_recipients",
        ["campaign_id", "status"],
    )
    op.create_index(
        "ix_marketing_recipients_lead_sent",
        "marketing_recipients",
        ["lead_id", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_recipients_lead_sent", table_name="marketing_recipients"
    )
    op.drop_index(
        "ix_marketing_recipients_campaign_status", table_name="marketing_recipients"
    )
    op.drop_index(
        "ix_marketing_recipients_organization_id", table_name="marketing_recipients"
    )
    op.drop_table("marketing_recipients")
    op.drop_index("ix_marketing_campaigns_project_id", table_name="marketing_campaigns")
    op.drop_index(
        "ix_marketing_campaigns_organization_id", table_name="marketing_campaigns"
    )
    op.drop_table("marketing_campaigns")
