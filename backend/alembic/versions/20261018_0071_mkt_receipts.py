"""Marketing recipients: provider message id and delivery receipts.

Revision ID: 0071_mkt_receipts
Revises: 0070_billing_webhook_events

Adds the provider's message id (to match receipts), the latest delivery state, and when it
was reported. Existing rows are left NULL. Downgrade drops the columns.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0071_mkt_receipts"
down_revision: Union[str, None] = "0070_billing_webhook_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_recipients",
        sa.Column("provider_message_id", sa.String(200), nullable=True),
    )
    op.add_column(
        "marketing_recipients",
        sa.Column("delivery_status", sa.String(20), nullable=True),
    )
    op.add_column(
        "marketing_recipients",
        sa.Column("delivery_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_marketing_recipients_provider_message_id",
        "marketing_recipients",
        ["provider_message_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_marketing_recipients_provider_message_id", table_name="marketing_recipients"
    )
    op.drop_column("marketing_recipients", "delivery_updated_at")
    op.drop_column("marketing_recipients", "delivery_status")
    op.drop_column("marketing_recipients", "provider_message_id")
