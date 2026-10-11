"""Audit log schemas (Phase 12, Module 5)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    action: str
    resource: str
    resource_id: Optional[str] = None
    before: Optional[dict[str, Any]] = None
    after: Optional[dict[str, Any]] = None
    meta: Optional[dict[str, Any]] = None
    created_at: datetime


class AuditLogActor(BaseModel):
    id: uuid.UUID
    name: Optional[str] = None
    email: Optional[str] = None


class AuditLogListResponse(BaseModel):
    logs: list[AuditLogOut]
    total: int
    limit: int
    offset: int
    actions: list[str]
    resources: list[str]
    actors: dict[str, AuditLogActor]
