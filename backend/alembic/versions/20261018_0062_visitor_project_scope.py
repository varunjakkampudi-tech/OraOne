"""Project scope for visitor memory, and backfill of project ownership.

Revision ID: 0062_visitor_project_scope
Revises: 0061_feature_flag_overrides

Visitor profiles were unique per organization, so one visitor could carry
memory across every project of an organization. This revision:

1. Adds ``visitor_profiles.project_id`` and backfills it from the
   organization's default project.
2. Backfills ``project_id`` on knowledge bases, widgets, agents and document
   chunks (chunks take their knowledge base's project). Rows with no project
   of their own move to the default project, so existing sites keep working.
3. Makes ``visitor_profiles.project_id`` mandatory and replaces the unique key
   with (organization_id, project_id, visitor_key).

Downgrade removes the project column. It fails if one visitor exists in two
projects, because the older unique key cannot hold both rows. Merge those rows
before downgrading.

The chunk backfill rewrites ``document_chunks``. On a large table, run this
during a maintenance window.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0062_visitor_project_scope"
down_revision: Union[str, None] = "0061_feature_flag_overrides"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# One live project per organization: the default, else the newest.
_DEFAULT_PROJECT = """
WITH default_project AS (
    SELECT DISTINCT ON (organization_id) id, organization_id
    FROM projects
    WHERE deleted_at IS NULL
    ORDER BY organization_id, is_default DESC, created_at DESC
)
"""


def upgrade() -> None:
    op.add_column(
        "visitor_profiles",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_visitor_profiles_project_id",
        "visitor_profiles",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="CASCADE",
    )

    for table in ("knowledge_bases", "widgets", "agents"):
        op.execute(
            _DEFAULT_PROJECT
            + f"""
            UPDATE {table} AS t
            SET project_id = dp.id
            FROM default_project dp
            WHERE t.organization_id = dp.organization_id
              AND t.project_id IS NULL
            """
        )

    # Chunks follow their knowledge base; anything left uses the default.
    op.execute(
        """
        UPDATE document_chunks AS c
        SET project_id = kb.project_id
        FROM knowledge_bases AS kb
        WHERE c.knowledge_base_id = kb.id
          AND kb.project_id IS NOT NULL
          AND c.project_id IS DISTINCT FROM kb.project_id
        """
    )
    op.execute(
        _DEFAULT_PROJECT
        + """
        UPDATE document_chunks AS c
        SET project_id = dp.id
        FROM default_project dp
        WHERE c.organization_id = dp.organization_id
          AND c.project_id IS NULL
        """
    )

    op.execute(
        _DEFAULT_PROJECT
        + """
        UPDATE visitor_profiles AS v
        SET project_id = dp.id
        FROM default_project dp
        WHERE v.organization_id = dp.organization_id
          AND v.project_id IS NULL
        """
    )
    # Fails loudly if an organization has no project at all, rather than
    # leaving memory unscoped.
    op.alter_column(
        "visitor_profiles",
        "project_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.drop_constraint(
        "uq_visitor_profiles_org_key", "visitor_profiles", type_="unique"
    )
    op.create_unique_constraint(
        "uq_visitor_profiles_org_project_key",
        "visitor_profiles",
        ["organization_id", "project_id", "visitor_key"],
    )
    op.create_index(
        "ix_visitor_profiles_project_id", "visitor_profiles", ["project_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_visitor_profiles_project_id", table_name="visitor_profiles")
    op.drop_constraint(
        "uq_visitor_profiles_org_project_key", "visitor_profiles", type_="unique"
    )
    op.create_unique_constraint(
        "uq_visitor_profiles_org_key",
        "visitor_profiles",
        ["organization_id", "visitor_key"],
    )
    op.drop_constraint(
        "fk_visitor_profiles_project_id", "visitor_profiles", type_="foreignkey"
    )
    op.drop_column("visitor_profiles", "project_id")
