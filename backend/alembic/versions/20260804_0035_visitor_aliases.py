"""Cross-channel identity merge: visitor_profiles.aliases.

Adds an ``aliases`` JSONB array of alternate resolution keys so two profiles
created on different channels (a browser token vs. a phone number) can be
folded into ONE identity without ever duplicating the visitor. Lookups match
``visitor_key = key OR aliases @> [key]``.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0035_visitor_aliases"
down_revision: Union[str, None] = "0034_visitor_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visitor_profiles",
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    # GIN index so ``aliases @> '["key"]'`` containment lookups stay fast.
    op.create_index(
        "ix_visitor_profiles_aliases",
        "visitor_profiles",
        ["aliases"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_visitor_profiles_aliases", table_name="visitor_profiles")
    op.drop_column("visitor_profiles", "aliases")
