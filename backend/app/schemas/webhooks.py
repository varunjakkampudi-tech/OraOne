"""Webhook schemas (R7 developer platform)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookEventInfo(BaseModel):
    event: str
    description: str


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    events: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(default=None, max_length=255)

    @field_validator("url")
    @classmethod
    def _https(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("https://") or v.startswith("http://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = Field(default=None, max_length=2048)
    events: Optional[List[str]] = None
    description: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = None


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: str
    success: bool
    status_code: Optional[int] = None
    attempts: int
    error: Optional[str] = None
    created_at: datetime


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    description: Optional[str] = None
    status: str
    events: List[str] = Field(default_factory=list)
    failure_count: int
    last_status: Optional[str] = None
    last_delivery_at: Optional[datetime] = None
    created_at: datetime


class WebhookCreateResponse(BaseModel):
    webhook: WebhookOut
    secret: str  # shown once


class WebhookListResponse(BaseModel):
    webhooks: List[WebhookOut]
    events: List[WebhookEventInfo]
