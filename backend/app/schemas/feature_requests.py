"""Schemas for the feature-request / feedback board."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.database.models.feature_request import (
    FeatureRequestPriority,
    FeatureRequestStatus,
    FeatureRequestType,
)


class FeatureRequestCreate(BaseModel):
    type: str = Field(default=FeatureRequestType.FEATURE)
    priority: str = Field(default=FeatureRequestPriority.MEDIUM)
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    author_name: Optional[str] = Field(default=None, max_length=160)


class FeatureRequestStatusUpdate(BaseModel):
    status: str


class FeatureRequestRead(BaseModel):
    id: uuid.UUID
    type: str
    priority: str
    status: str
    title: str
    description: Optional[str]
    votes: int
    has_voted: bool
    is_author: bool
    author_name: Optional[str]
    created_at: datetime
    updated_at: datetime


class FeatureRequestListResponse(BaseModel):
    items: list[FeatureRequestRead]
    total: int


class FeatureRequestStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
