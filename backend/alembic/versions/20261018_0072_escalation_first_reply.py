"""Escalations: record when the team first replied to the customer.

Revision ID: 0072_escalation_first_reply
Revises: 0071_mkt_receipts

Adds ``escalations.first_reply_at``. Existing rows are left NULL. Downgrade drops the column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0072_escalation_first_reply"
down_revision: Union[str, None] = "0071_mkt_receipts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "escalations",
        sa.Column("first_reply_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("escalations", "first_reply_at")
