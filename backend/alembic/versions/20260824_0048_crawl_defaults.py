"""Deeper, broader default crawl coverage.

Raises the default crawl budget for newly-registered websites so a fresh
crawl reaches "all the important pages" like a search-engine bot instead of
stopping short: ``max_pages`` 200 → 500 and ``max_depth`` 3 → 5. Existing
website rows keep their configured values — only the column DEFAULT changes,
so new sites (including agent auto-crawls) inherit the broader budget.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0048_crawl_defaults"
down_revision: Union[str, None] = "0047_ticket_priority"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "websites", "max_pages",
        existing_type=sa.Integer(), existing_nullable=False,
        server_default="500",
    )
    op.alter_column(
        "websites", "max_depth",
        existing_type=sa.Integer(), existing_nullable=False,
        server_default="5",
    )


def downgrade() -> None:
    op.alter_column(
        "websites", "max_pages",
        existing_type=sa.Integer(), existing_nullable=False,
        server_default="200",
    )
    op.alter_column(
        "websites", "max_depth",
        existing_type=sa.Integer(), existing_nullable=False,
        server_default="3",
    )
