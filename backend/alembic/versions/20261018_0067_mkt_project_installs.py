"""Marketplace installs belong to a project; one active install per project and blueprint.

Revision ID: 0067_mkt_project_installs
Revises: 0066_escalation_inbox

Backfills ``marketplace_installations.project_id`` from the installed agent's
project, falling back to the organization's default project. Adds a partial
unique index so two concurrent installs of the same blueprint in one project
cannot both succeed. Downgrade removes the index only; the project column stays.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0067_mkt_project_installs"
down_revision: Union[str, None] = "0066_escalation_inbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE marketplace_installations AS mi
        SET project_id = a.project_id
        FROM agents AS a
        WHERE mi.project_id IS NULL
          AND mi.agent_id = a.id
          AND a.project_id IS NOT NULL
        """
    )
    op.execute(
        """
        WITH default_project AS (
            SELECT DISTINCT ON (organization_id) id, organization_id
            FROM projects
            WHERE deleted_at IS NULL
            ORDER BY organization_id, is_default DESC, created_at DESC
        )
        UPDATE marketplace_installations AS mi
        SET project_id = dp.id
        FROM default_project AS dp
        WHERE mi.project_id IS NULL
          AND mi.organization_id = dp.organization_id
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_marketplace_active_install
        ON marketplace_installations (organization_id, project_id, listing_slug)
        WHERE status = 'installed'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_marketplace_active_install")
