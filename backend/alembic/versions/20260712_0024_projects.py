"""Projects layer — workspace hierarchy between Organization and resources.

Introduces the ``projects`` table and adds a nullable ``project_id`` FK to
every core resource table (agents, knowledge_bases, conversations,
workflows, websites, widgets, integrations, webhook_endpoints, api_keys,
documents, document_chunks).

Backfill is non-destructive:
  1. Create exactly one ``Default`` project (``is_default = true``) per
     existing organization.
  2. Point every existing resource at its org's default project.

Columns stay nullable so the change is backward-compatible with the
running app until the API/UI start setting ``project_id`` explicitly.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0024_projects"
down_revision: Union[str, None] = "0023_collaboration_security"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Resource tables that own a non-nullable organization_id and get a
# project_id backfilled by org → default project.
_RESOURCE_TABLES = [
    "agents",
    "knowledge_bases",
    "conversations",
    "workflows",
    "websites",
    "widgets",
    "integrations",
    "webhook_endpoints",
    "api_keys",
    "documents",
]


def upgrade() -> None:
    # ── 1. project_status enum ──
    project_status = postgresql.ENUM(
        "active", "archived", name="project_status"
    )
    project_status.create(op.get_bind(), checkfirst=True)

    # ── 2. projects table ──
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("active", "archived", name="project_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("icon", sa.String(length=40), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_projects_org_slug"),
        if_not_exists=True,
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"], if_not_exists=True)
    op.create_index("ix_projects_status", "projects", ["status"], if_not_exists=True)

    # ── 3. project_id columns on resource tables (+ chunks) ──
    for table in _RESOURCE_TABLES + ["document_chunks"]:
        op.add_column(
            table,
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_index(
            f"ix_{table}_project_id", table, ["project_id"], if_not_exists=True
        )
        op.create_foreign_key(
            f"fk_{table}_project_id",
            table,
            "projects",
            ["project_id"],
            ["id"],
            ondelete="CASCADE",
        )

    # ── 4. backfill: one default project per org ──
    op.execute(
        """
        INSERT INTO projects (
            id, organization_id, name, slug, status, is_default,
            settings, created_at, updated_at
        )
        SELECT gen_random_uuid(), o.id, 'Default', 'default', 'active', true,
               '{}'::jsonb, now(), now()
        FROM organizations o
        WHERE NOT EXISTS (
            SELECT 1 FROM projects p
            WHERE p.organization_id = o.id AND p.is_default = true
        )
        """
    )

    # ── 5. backfill: point existing resources at their default project ──
    for table in _RESOURCE_TABLES:
        op.execute(
            f"""
            UPDATE {table} t
            SET project_id = p.id
            FROM projects p
            WHERE p.organization_id = t.organization_id
              AND p.is_default = true
              AND t.project_id IS NULL
            """
        )

    # document_chunks has a nullable organization_id (website chunks).
    op.execute(
        """
        UPDATE document_chunks dc
        SET project_id = p.id
        FROM projects p
        WHERE p.organization_id = dc.organization_id
          AND p.is_default = true
          AND dc.project_id IS NULL
          AND dc.organization_id IS NOT NULL
        """
    )


def downgrade() -> None:
    for table in _RESOURCE_TABLES + ["document_chunks"]:
        op.drop_constraint(f"fk_{table}_project_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_project_id", table_name=table)
        op.drop_column(table, "project_id")

    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_table("projects")
    postgresql.ENUM(name="project_status").drop(op.get_bind(), checkfirst=True)
