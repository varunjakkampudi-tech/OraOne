"""Pydantic schemas for the Leads (CRM) API."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# Display labels match the dashboard's STATUS_CLS keys (title-case).
STATUS_LABELS = {
    "new": "New",
    "contacted": "Contacted",
    "qualified": "Qualified",
    "won": "Won",
    "lost": "Lost",
}


class LeadCreate(BaseModel):
    """Manually create a lead (or via API)."""

    name: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    company: Optional[str] = Field(default=None, max_length=200)
    intent: Optional[str] = Field(default=None, max_length=255)
    message: Optional[str] = Field(default=None, max_length=4000)
    source: str = Field(default="manual", max_length=40)
    status: Optional[str] = Field(default=None, description="new|contacted|qualified|won|lost")
    temperature: Optional[str] = Field(default=None, description="hot|warm|cold")
    score: Optional[int] = Field(default=None, ge=0, le=100)


class LeadUpdate(BaseModel):
    """Partial update — pipeline + contact edits."""

    name: Optional[str] = Field(default=None, max_length=160)
    email: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=40)
    company: Optional[str] = Field(default=None, max_length=200)
    intent: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = Field(default=None, description="new|contacted|qualified|won|lost")
    temperature: Optional[str] = Field(default=None, description="hot|warm|cold")
    score: Optional[int] = Field(default=None, ge=0, le=100)
    assigned_to: Optional[uuid.UUID] = None
    notes: Optional[str] = Field(default=None, max_length=4000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)


class LeadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    conversation_id: Optional[uuid.UUID] = None
    agent_id: Optional[uuid.UUID] = None
    widget_id: Optional[uuid.UUID] = None
    assigned_to: Optional[uuid.UUID] = None

    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    intent: Optional[str] = None
    message: Optional[str] = None

    source: str
    # Title-case label so the dashboard badge styling matches directly.
    status: str
    temperature: str
    score: int

    # CRM annotations, persisted in the lead's ``extra`` JSONB blob.
    notes: Optional[str] = None
    tags: list[str] = []

    created_at: datetime
    updated_at: datetime


class LeadStats(BaseModel):
    total: int = 0
    new: int = 0
    contacted: int = 0
    qualified: int = 0
    won: int = 0
    lost: int = 0
    hot: int = 0
    warm: int = 0
    cold: int = 0
    conversion_rate: float = 0.0  # won / total, as a percentage 0-100
    appointments: int = 0


class LeadConversationMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[datetime] = None


class LeadConversationRead(BaseModel):
    """The chat thread that produced a lead — shown inline in the CRM."""

    conversation_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[datetime] = None
    messages: list[LeadConversationMessage] = []
