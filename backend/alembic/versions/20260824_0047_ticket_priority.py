"""Support ticket priority.

Adds a ``priority`` column to ``feature_requests`` so submissions become
prioritised support tickets (low / medium / high / urgent) alongside the
existing type (feature / bug / help / feedback).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0047_ticket_priority"
down_revision: Union[str, None] = "0046_contact_forms"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "feature_requests",
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="medium",
        ),
    )


def downgrade() -> None:
    op.drop_column("feature_requests", "priority")
