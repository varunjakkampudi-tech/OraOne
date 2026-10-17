"""Pydantic schemas for the marketing campaigns API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    channel: str = Field(min_length=1, max_length=16, description="email|sms|whatsapp")
    subject: Optional[str] = Field(
        default=None, max_length=200, description="Required for email"
    )
    body: str = Field(min_length=1, max_length=10_000)
    lead_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    channel: str
    subject: Optional[str] = None
    body: str
    status: str
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    sent_count: int
    skipped_count: int
    failed_count: int


class RecipientRead(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID
    lead_label: str
    status: str
    skip_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    sent_at: Optional[datetime] = None


class CampaignDetail(CampaignRead):
    queued_count: int
    recipients: list[RecipientRead]
