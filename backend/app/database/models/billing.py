"""Billing models (Phase 12, Module 1).

Plans are global catalogue rows (free / starter / business / enterprise).
Subscriptions and invoices are tenant-scoped (one active subscription per
organization). Stripe identifiers are stored when real Stripe is wired up;
in mock mode they stay null and the subscription is activated directly.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.database.models.organization import Organization


class PlanCode(str, enum.Enum):
    free = "free"
    starter = "starter"
    business = "business"
    enterprise = "enterprise"


class BillingCycle(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trialing = "trialing"
    past_due = "past_due"
    canceled = "canceled"
    incomplete = "incomplete"


class InvoiceStatus(str, enum.Enum):
    paid = "paid"
    open = "open"
    void = "void"


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A purchasable subscription tier (global catalogue, not org-scoped)."""

    __tablename__ = "plans"
    __table_args__ = (
        UniqueConstraint("code", name="uq_plans_code"),
        Index("ix_plans_sort_order", "sort_order"),
    )

    code: Mapped[PlanCode] = mapped_column(
        Enum(PlanCode, name="plan_code"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(400))
    # Monthly list price in the smallest currency unit (e.g. cents/paise).
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Yearly list price (usually = monthly * 10, i.e. 2 months free).
    price_cents_yearly: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    features: Mapped[list[Any]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    # Quota dictionary, e.g. {"users": 10, "agents": 20, "storage_mb": 20480}.
    # A value of -1 means unlimited.
    limits: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Plan {self.code}>"


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One organization's current subscription. One row per org."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_subscriptions_org"),
        Index("ix_subscriptions_plan_id", "plan_id"),
        Index("ix_subscriptions_status", "status"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("plans.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.active,
    )
    billing_cycle: Mapped[BillingCycle] = mapped_column(
        Enum(BillingCycle, name="billing_cycle"),
        nullable=False,
        default=BillingCycle.monthly,
    )
    current_period_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(80))
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(80))

    plan: Mapped["Plan"] = relationship(lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Subscription org={self.organization_id} status={self.status}>"


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A billing invoice (generated on activation / renewal)."""

    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_organization_id", "organization_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    subscription_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
    )
    number: Mapped[str] = mapped_column(String(40), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="usd")
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        nullable=False,
        default=InvoiceStatus.paid,
    )
    description: Mapped[Optional[str]] = mapped_column(String(200))
    hosted_url: Mapped[Optional[str]] = mapped_column(String(500))
    stripe_invoice_id: Mapped[Optional[str]] = mapped_column(String(80))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Invoice {self.number} {self.amount_cents}{self.currency}>"
