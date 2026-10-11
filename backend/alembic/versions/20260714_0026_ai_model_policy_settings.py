"""AI model policy settings — routing strategy, cost & latency limits.

Adds a single nullable ``settings`` JSONB column to ``ai_model_policies``
to hold the org's routing rules without further schema churn:

* ``routing_strategy`` — balanced | cheapest | fastest | quality
* ``monthly_budget_usd`` — soft monthly spend cap (downgrades to cheapest)
* ``max_latency_ms`` — drop models slower than this from routing
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0026_ai_model_policy_settings"
down_revision: Union[str, None] = "0025_leads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_model_policies",
        sa.Column(
            "settings",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_model_policies", "settings")
