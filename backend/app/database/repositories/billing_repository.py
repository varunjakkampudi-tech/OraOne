"""Billing repository (Phase 12, Module 1).

Plans are global; subscriptions and invoices are tenant-scoped. The
subscription helpers are pinned to ``organization_id``.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.billing import Invoice, Plan, Subscription


class BillingRepository:
    def __init__(self, session: AsyncSession, organization_id: uuid.UUID) -> None:
        self.session = session
        self.organization_id = organization_id

    # ── plans (global) ──
    async def list_plans(self) -> list[Plan]:
        q = (
            select(Plan)
            .where(Plan.is_active.is_(True))
            .order_by(Plan.sort_order, Plan.price_cents)
        )
        return list((await self.session.scalars(q)).all())

    async def get_plan_by_code(self, code: str) -> Optional[Plan]:
        q = select(Plan).where(Plan.code == code)
        return await self.session.scalar(q)

    async def get_plan(self, plan_id: uuid.UUID) -> Optional[Plan]:
        return await self.session.get(Plan, plan_id)

    # ── subscription (org-scoped) ──
    async def get_subscription(self) -> Optional[Subscription]:
        q = select(Subscription).where(
            Subscription.organization_id == self.organization_id
        )
        return await self.session.scalar(q)

    # ── invoices (org-scoped) ──
    async def list_invoices(self, *, limit: int = 50, offset: int = 0) -> list[Invoice]:
        q = (
            select(Invoice)
            .where(Invoice.organization_id == self.organization_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self.session.scalars(q)).all())

    async def count_invoices(self) -> int:
        q = select(func.count(Invoice.id)).where(
            Invoice.organization_id == self.organization_id
        )
        return int((await self.session.scalar(q)) or 0)
