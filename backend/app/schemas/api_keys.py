"""API key request/response schemas (Phase 12, Module 9)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ScopeOption(BaseModel):
    scope: str
    label: str


class ApiKeyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    prefix: str
    scopes: List[str]
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    scopes: List[str] = Field(..., min_length=1)
    expires_at: Optional[datetime] = None


class ApiKeyCreateResponse(BaseModel):
    """Returned once on creation. ``key`` is the only time the secret is shown."""

    key: str
    api_key: ApiKeyOut


class ApiKeyListResponse(BaseModel):
    keys: List[ApiKeyOut]
    scopes: List[ScopeOption]
