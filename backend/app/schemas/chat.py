"""Request/response schemas for the AI chat surface (Phase 8)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Conversations ────────────────

class ConversationCreate(BaseModel):
    agent_id: uuid.UUID
    title: Optional[str] = Field(default=None, max_length=255)


class ConversationRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class ChatConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_message_at: Optional[datetime] = None
    is_pinned: bool = False
    is_archived: bool = False
    is_favorite: bool = False
    folder_id: Optional[uuid.UUID] = None
    tags: list[str] = Field(default_factory=list)
    share_token: Optional[str] = None
    shared_at: Optional[datetime] = None


class ConversationPatch(BaseModel):
    """Flexible partial update for organization flags & metadata."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    is_favorite: Optional[bool] = None
    folder_id: Optional[uuid.UUID] = None
    clear_folder: bool = False
    tags: Optional[list[str]] = None
    status: Optional[str] = None


# ──────────────── Folders ────────────────

class FolderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    color: Optional[str] = Field(default=None, max_length=9)
    icon: Optional[str] = Field(default=None, max_length=40)


class FolderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    color: Optional[str] = Field(default=None, max_length=9)
    icon: Optional[str] = Field(default=None, max_length=40)


class FolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: Optional[str] = None
    icon: Optional[str] = None
    conversation_count: int = 0
    created_at: datetime
    updated_at: datetime


# ──────────────── Sharing & suggestions ────────────────

class ShareResult(BaseModel):
    share_token: Optional[str] = None
    shared_at: Optional[datetime] = None
    share_url: Optional[str] = None
    is_shared: bool = False


class SuggestedQuestions(BaseModel):
    questions: list[str] = Field(default_factory=list)


class PublicMessage(BaseModel):
    role: str
    content: str
    created_at: datetime


class PublicConversation(BaseModel):
    title: Optional[str] = None
    agent_name: Optional[str] = None
    shared_at: Optional[datetime] = None
    messages: list[PublicMessage] = Field(default_factory=list)


# ──────────────── Messages ────────────────

class MessageSend(BaseModel):
    content: str = Field(..., min_length=1)
    use_knowledge: bool = True
    history_limit: int = Field(default=20, ge=1, le=100)


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    token_count: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class SendMessageResult(BaseModel):
    conversation_id: uuid.UUID
    title: Optional[str] = None
    user_message: ChatMessageOut
    assistant_message: ChatMessageOut
    usage: dict[str, int] = Field(default_factory=dict)
    context_used: int = 0
    sources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Citations for the retrieved context: document, page, section, score.",
    )
