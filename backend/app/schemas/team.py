"""Pydantic schemas for the Team API (Phase 12, Module 3)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class MemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    status: str
    joined_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    is_you: bool = False


class MemberListResponse(BaseModel):
    items: List[MemberRead]
    total: int


class RoleUpdateRequest(BaseModel):
    role: str


class InvitationRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    status: str
    invited_by: Optional[str] = None
    invite_url: Optional[str] = None
    expires_at: datetime
    created_at: datetime
    accepted_at: Optional[datetime] = None


class InvitationListResponse(BaseModel):
    items: List[InvitationRead]
    total: int


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InviteCreateResponse(BaseModel):
    invitation: InvitationRead
    message: str


class InviteAcceptRequest(BaseModel):
    token: str


class InviteAcceptResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    role: str
    message: str


class InvitePreviewResponse(BaseModel):
    valid: bool
    organization_name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
