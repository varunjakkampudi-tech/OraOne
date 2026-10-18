"""Marketing recipients: record when a worker claimed them for sending.

Revision ID: 0069_mkt_claimed_at
Revises: 0068_escalation_one_open

Adds ``marketing_recipients.claimed_at``. Existing rows are left NULL. Downgrade
drops the column.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0069_mkt_claimed_at"
down_revision: Union[str, None] = "0068_escalation_one_open"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_recipients",
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("marketing_recipients", "claimed_at")
