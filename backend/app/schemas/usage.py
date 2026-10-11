"""Pydantic schemas for the usage metering API (Phase 12, Module 2)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UsageMetric(BaseModel):
    metric: str
    label: str
    category: str  # "resource" | "metered"
    used: int
    limit: int  # -1 = unlimited
    unlimited: bool
    percent: int
    period: Optional[str] = None


class UsageSnapshotResponse(BaseModel):
    plan_code: str
    plan_name: str
    metrics: list[UsageMetric]
    generated_at: datetime


class QuotaCheckResponse(BaseModel):
    metric: str
    allowed: bool
    used: int
    limit: int
    remaining: Optional[int] = None
    unlimited: bool


class RecordUsageRequest(BaseModel):
    metric: str
    amount: int = Field(default=1, ge=1, le=10000)


class RecordUsageResponse(BaseModel):
    metric: str
    period_total: int
