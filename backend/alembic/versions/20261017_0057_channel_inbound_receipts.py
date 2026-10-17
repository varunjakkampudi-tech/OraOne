"""Channel inbound receipts: dedupe redelivered provider webhooks per agent.

Revision ID: 0057_channel_inbound_receipts
Revises: 0056_widget_session_token_hash

Adds ``channel_inbound_receipts`` with a unique ``(agent_id, message_key)``. The inbound
pipeline inserts the provider's message id here before replying, so a second delivery of
the same webhook hits the constraint and produces no second reply.

Downgrade drops the table and its receipts; re-delivered webhooks would then be answered
again, so downgrade only when the inbound channels are disabled.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0057_channel_inbound_receipts"
down_revision: Union[str, Sequence[str], None] = "0056_widget_session_token_hash"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "channel_inbound_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("message_key", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "agent_id", "message_key", name="uq_channel_inbound_receipts_agent_key"
        ),
    )
    op.create_index(
        "ix_channel_inbound_receipts_organization_id",
        "channel_inbound_receipts",
        ["organization_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_channel_inbound_receipts_organization_id",
        table_name="channel_inbound_receipts",
    )
    op.drop_table("channel_inbound_receipts")
