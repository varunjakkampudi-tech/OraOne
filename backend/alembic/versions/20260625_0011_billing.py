"""Phase 12 Module 1: billing (plans, subscriptions, invoices).

Creates the ``plans`` catalogue, the per-org ``subscriptions`` table, and
an ``invoices`` table. Plans are seeded at application startup
(``ensure_plans_seeded``) so this migration only builds structure.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0011_billing"
down_revision: Union[str, None] = "0010_workflow_phase11_expansion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    plan_code = postgresql.ENUM(
        "free", "starter", "business", "enterprise", name="plan_code"
    )
    billing_cycle = postgresql.ENUM("monthly", "yearly", name="billing_cycle")
    sub_status = postgresql.ENUM(
        "active", "trialing", "past_due", "canceled", "incomplete",
        name="subscription_status",
    )
    invoice_status = postgresql.ENUM("paid", "open", "void", name="invoice_status")
    for e in (plan_code, billing_cycle, sub_status, invoice_status):
        e.create(bind, checkfirst=True)

    # The enums are created explicitly above; prevent create_table from
    # re-emitting CREATE TYPE for the columns that reference them.
    for e in (plan_code, billing_cycle, sub_status, invoice_status):
        e.create_type = False

    op.create_table(
        "plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", plan_code, nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=400), nullable=True),
        sa.Column("price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("price_cents_yearly", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("features", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("limits", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("code", name="uq_plans_code"),
        if_not_exists=True,
    )
    op.create_index("ix_plans_sort_order", "plans", ["sort_order"], if_not_exists=True)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "plan_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("status", sub_status, nullable=False, server_default="active"),
        sa.Column("billing_cycle", billing_cycle, nullable=False, server_default="monthly"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("stripe_customer_id", sa.String(length=80), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", name="uq_subscriptions_org"),
        if_not_exists=True,
    )
    op.create_index("ix_subscriptions_plan_id", "subscriptions", ["plan_id"], if_not_exists=True)
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], if_not_exists=True)

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column(
            "subscription_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True,
        ),
        sa.Column("number", sa.String(length=40), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("status", invoice_status, nullable=False, server_default="paid"),
        sa.Column("description", sa.String(length=200), nullable=True),
        sa.Column("hosted_url", sa.String(length=500), nullable=True),
        sa.Column("stripe_invoice_id", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        if_not_exists=True,
    )
    op.create_index("ix_invoices_organization_id", "invoices", ["organization_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("invoices")
    op.drop_table("subscriptions")
    op.drop_table("plans")
    for name in ("invoice_status", "subscription_status", "billing_cycle", "plan_code"):
        op.execute(f"DROP TYPE IF EXISTS {name}")
