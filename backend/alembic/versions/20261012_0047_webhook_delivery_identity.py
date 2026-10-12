"""Add durable per-event webhook delivery identity."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0050_webhook_delivery_identity"
down_revision: Union[str, Sequence[str], None] = "0045_platform_roles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "webhook_deliveries",
        sa.Column("event_id", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "uq_webhook_deliveries_endpoint_event_id",
        "webhook_deliveries",
        ["endpoint_id", "event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_webhook_deliveries_endpoint_event_id", table_name="webhook_deliveries"
    )
    op.drop_column("webhook_deliveries", "event_id")
