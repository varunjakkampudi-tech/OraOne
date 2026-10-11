"""R10 — Security & Operations request schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    text: str = Field(..., min_length=1)
    direction: str = Field("input", pattern="^(input|output)$")


class FeatureFlagUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    enabled: bool = False
    description: Optional[str] = Field(None, max_length=500)
    environment: str = Field("production", max_length=20)
    rollout_percentage: int = Field(100, ge=0, le=100)


class FeatureFlagToggleRequest(BaseModel):
    enabled: bool


class DeploymentRecordRequest(BaseModel):
    version: str = Field(..., min_length=1, max_length=40)
    environment: str = Field("production", max_length=20)
    status: str = Field("succeeded", max_length=20)
    notes: Optional[str] = None
