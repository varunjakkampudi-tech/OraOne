"""Pydantic schemas for the Embedded Website Widget API (R6).

Two surfaces:
* **Admin** (org-scoped, authenticated) — create/configure/publish widgets.
* **Public** (unauthenticated, domain-restricted) — the loader config and
  the visitor chat/escalate/feedback/event endpoints.

Public responses NEVER expose org internals beyond what the embedded
experience needs (agent name, theme, suggested questions, …).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────── Theme / settings (shared shape) ────────────────

class WidgetTheme(BaseModel):
    primary_color: str = "#2563EB"
    secondary_color: str = "#0EA5E9"
    background_color: str = "#FFFFFF"
    text_color: str = "#0F172A"
    bubble_color: str = "#2563EB"
    mode: str = "light"          # light | dark | auto
    font_family: Optional[str] = None
    radius: str = "20px"
    logo_url: Optional[str] = None
    avatar_url: Optional[str] = None
    launcher_icon: Optional[str] = None


class WidgetSettings(BaseModel):
    company_name: Optional[str] = None
    agent_name: str = "Ora AI"
    welcome_message: str = "Hi! 👋 How can I help you today?"
    input_placeholder: str = "Ask a question…"
    suggested_questions: list[str] = Field(default_factory=list)
    show_branding: bool = True              # "Powered by OraOne"
    collect_leads: bool = True
    lead_fields: list[str] = Field(default_factory=lambda: ["name", "email"])
    allow_file_upload: bool = False
    enable_escalation: bool = True
    offline_message: Optional[str] = None
    popup_delay_seconds: int = 30
    languages: list[str] = Field(default_factory=lambda: ["en"])
    rate_limit_per_min: int = 20


# ──────────────── Admin: CRUD ────────────────

class WidgetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    agent_id: Optional[uuid.UUID] = None
    knowledge_base_id: Optional[uuid.UUID] = None
    widget_type: str = "bubble"
    position: str = "bottom-right"
    auth_mode: str = "public"
    theme: WidgetTheme = Field(default_factory=WidgetTheme)
    settings: WidgetSettings = Field(default_factory=WidgetSettings)
    domains: list[str] = Field(default_factory=list)


class WidgetUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    agent_id: Optional[uuid.UUID] = None
    knowledge_base_id: Optional[uuid.UUID] = None
    widget_type: Optional[str] = None
    position: Optional[str] = None
    auth_mode: Optional[str] = None
    status: Optional[str] = None
    theme: Optional[WidgetTheme] = None
    settings: Optional[WidgetSettings] = None
    domains: Optional[list[str]] = None


class WidgetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    public_key: str
    name: str
    status: str
    widget_type: str
    position: str
    auth_mode: str
    agent_id: Optional[uuid.UUID] = None
    knowledge_base_id: Optional[uuid.UUID] = None
    theme: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    domains: list[str] = Field(default_factory=list)
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Embed convenience
    embed_snippet: Optional[str] = None
    sessions_count: Optional[int] = None


class WidgetListResponse(BaseModel):
    items: list[WidgetRead]
    total: int


# ──────────────── Public: loader config ────────────────

class WidgetPublicConfig(BaseModel):
    """Sanitized config the loader fetches by public_key. No secrets."""

    public_key: str
    name: str
    status: str
    widget_type: str
    position: str
    auth_mode: str
    theme: WidgetTheme
    settings: WidgetSettings
    agent_name: str
    has_knowledge: bool


# ──────────────── Public: session + chat ────────────────

class WidgetSessionStart(BaseModel):
    public_key: str
    visitor_id: Optional[str] = None
    user_context: dict[str, Any] = Field(default_factory=dict)


class WidgetSessionRead(BaseModel):
    session_id: uuid.UUID
    visitor_id: str
    conversation_id: Optional[uuid.UUID] = None
    messages: list[dict[str, Any]] = Field(default_factory=list)


class WidgetChatRequest(BaseModel):
    public_key: str
    visitor_id: str
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[uuid.UUID] = None
    user_context: dict[str, Any] = Field(default_factory=dict)


class WidgetChatSource(BaseModel):
    type: str = "document"
    title: Optional[str] = None
    url: Optional[str] = None
    page: Optional[int] = None
    score: Optional[float] = None


class WidgetChatResponse(BaseModel):
    answer: str
    sources: list[WidgetChatSource] = Field(default_factory=list)
    confidence: float = 0.0
    related_questions: list[str] = Field(default_factory=list)
    grounded: bool = False
    session_id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None


# ──────────────── Public: escalate / lead / feedback / event ────────────────

class WidgetLeadRequest(BaseModel):
    public_key: str
    visitor_id: str
    session_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    message: Optional[str] = None


class WidgetEscalateRequest(BaseModel):
    public_key: str
    visitor_id: str
    session_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None


class WidgetFeedbackRequest(BaseModel):
    public_key: str
    visitor_id: str
    session_id: Optional[uuid.UUID] = None
    message_id: Optional[uuid.UUID] = None
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class WidgetEventRequest(BaseModel):
    public_key: str
    visitor_id: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    event: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class WidgetOk(BaseModel):
    ok: bool = True
    detail: Optional[str] = None


# ──────────────── Admin: analytics ────────────────

class WidgetAnalytics(BaseModel):
    widget_id: uuid.UUID
    status: str
    sessions: int = 0
    conversations: int = 0
    messages: int = 0
    opens: int = 0
    leads: int = 0
    escalations: int = 0
    bookings: int = 0
    errors: int = 0
    avg_csat: Optional[float] = None
    by_event: dict[str, int] = Field(default_factory=dict)
    top_questions: list[dict[str, Any]] = Field(default_factory=list)
