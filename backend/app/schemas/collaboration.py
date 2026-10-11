"""R9 — Collaboration request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field


# ── teams ──
class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=40)


class TeamUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, max_length=20)
    icon: Optional[str] = Field(None, max_length=40)


class TeamMemberAddRequest(BaseModel):
    user_id: uuid.UUID
    role: str = Field("contributor", max_length=20)


# ── sharing ──
class ShareRequest(BaseModel):
    resource_type: str = Field(..., max_length=40)
    resource_id: str = Field(..., max_length=80)
    principal_type: str = Field(..., max_length=20)  # user | team | organization
    principal_id: Optional[str] = Field(None, max_length=80)
    permission: str = Field("viewer", max_length=20)  # owner|editor|commenter|viewer


# ── comments ──
class CommentCreateRequest(BaseModel):
    resource_type: str = Field(..., max_length=40)
    resource_id: str = Field(..., max_length=80)
    body: str = Field(..., min_length=1)
    parent_comment_id: Optional[uuid.UUID] = None
    mention_user_ids: List[str] = Field(default_factory=list)


class CommentResolveRequest(BaseModel):
    resolved: bool = True


class ReactionRequest(BaseModel):
    resource_type: str = Field(..., max_length=40)
    resource_id: str = Field(..., max_length=80)
    emoji: str = Field(..., max_length=16)


# ── tasks ──
class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    assignee_user_id: Optional[uuid.UUID] = None
    resource_type: Optional[str] = Field(None, max_length=40)
    resource_id: Optional[str] = Field(None, max_length=80)
    comment_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None


class TaskUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=20)
    assignee_user_id: Optional[uuid.UUID] = None


# ── follows ──
class FollowRequest(BaseModel):
    resource_type: str = Field(..., max_length=40)
    resource_id: str = Field(..., max_length=80)
