"""Pydantic schemas for the Billing API (Phase 12, Module 1)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class PlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    price_cents: int
    price_cents_yearly: int
    currency: str
    features: list[Any]
    limits: dict[str, Any]
    is_active: bool
    sort_order: int


class PlanListResponse(BaseModel):
    items: list[PlanRead]
    total: int


class SubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    plan_id: uuid.UUID
    status: str
    billing_cycle: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: datetime


class SubscriptionDetail(SubscriptionRead):
    plan: PlanRead


class CheckoutRequest(BaseModel):
    plan_code: str = Field(min_length=1, max_length=40)
    billing_cycle: str = "monthly"


class CheckoutResponse(BaseModel):
    mode: str  # "mock" | "stripe"
    checkout_url: Optional[str] = None
    activated: bool = False
    subscription: Optional[SubscriptionDetail] = None
    message: Optional[str] = None


class PortalResponse(BaseModel):
    mode: str
    portal_url: Optional[str] = None
    message: Optional[str] = None


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    amount_cents: int
    currency: str
    status: str
    description: Optional[str] = None
    hosted_url: Optional[str] = None
    created_at: datetime


class InvoiceListResponse(BaseModel):
    items: list[InvoiceRead]
    total: int
