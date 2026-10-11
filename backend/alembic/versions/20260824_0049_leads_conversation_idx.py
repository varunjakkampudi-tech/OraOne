"""Index leads.conversation_id.

Every website conversation now materialises a lead (deduped on the
conversation), so lookups by ``conversation_id`` happen on the chat hot path
and as the ``leads`` table grows. Add the supporting index.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "0049_leads_conversation_idx"
down_revision: Union[str, None] = "0048_crawl_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_leads_conversation_id", "leads", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_conversation_id", table_name="leads")
