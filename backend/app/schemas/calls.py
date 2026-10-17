"""Pydantic schemas for the outbound calling API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignCreate(BaseModel):
    """Choose leads either by id or by pipeline filter (at least one is required)."""

    name: str = Field(min_length=1, max_length=120)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)
    lead_ids: Optional[list[uuid.UUID]] = Field(default=None, max_length=1000)
    lead_status: Optional[str] = Field(
        default=None, description="new|contacted|qualified|won|lost"
    )
    lead_temperature: Optional[str] = Field(default=None, description="hot|warm|cold")

    @model_validator(mode="after")
    def _needs_a_selection(self) -> "CampaignCreate":
        if not self.lead_ids and not self.lead_status and not self.lead_temperature:
            raise ValueError(
                "Choose leads by lead_ids or by lead_status / lead_temperature."
            )
        return self


class CampaignCounts(BaseModel):
    total: int = 0
    queued: int = 0
    calling: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    status: str
    timezone: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    counts: CampaignCounts


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: uuid.UUID
    status: str
    skip_reason: Optional[str] = None
    twilio_call_sid: Optional[str] = None
    attempted_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    outcome: Optional[str] = None
