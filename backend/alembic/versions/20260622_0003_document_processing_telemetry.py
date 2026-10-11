"""Document-processing telemetry columns (Phase 7).

Adds three nullable columns to ``documents`` so the processor can record
when work started, when it finished, and the failure reason (if any).
The dashboard derives processing time from the two timestamps.

* ``processing_started_at``
* ``processing_completed_at``
* ``processing_error``
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0003_doc_processing_telemetry"
down_revision: Union[str, None] = "0002_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(
            sa.Column("processing_started_at", sa.DateTime(timezone=True))
        )
        batch.add_column(
            sa.Column("processing_completed_at", sa.DateTime(timezone=True))
        )
        batch.add_column(sa.Column("processing_error", sa.String(1000)))


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("processing_error")
        batch.drop_column("processing_completed_at")
        batch.drop_column("processing_started_at")
