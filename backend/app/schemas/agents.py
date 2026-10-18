"""Agent request/response schemas (Phase 6)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=160)
    type: str = Field(..., description="Agent type: chat, whatsapp, sales, support.")
    description: Optional[str] = None
    model: Optional[str] = Field(default=None, max_length=80)
    status: Optional[str] = Field(
        default=None, description="Initial status; defaults to 'draft'."
    )
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    website_url: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Site to auto-crawl into the knowledge base on deploy.",
    )

    # AgentConfig fields (1:1 sidecar — created in the same transaction)
    system_prompt: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    voice: Optional[str] = Field(default=None, max_length=80)
    language: Optional[str] = Field(default=None, max_length=16)
    greeting: Optional[str] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = Field(
        default=None,
        max_length=100,
        description=(
            "Knowledge bases explicitly bound to this agent. Omitted means no "
            "explicit binding; an empty list is preserved as an explicit selection."
        ),
    )


class AgentUpdate(BaseModel):
    """All fields optional — partial update."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=160)
    type: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = Field(default=None, max_length=80)
    status: Optional[str] = None
    avatar_url: Optional[str] = Field(default=None, max_length=500)
    website_url: Optional[str] = Field(default=None, max_length=500)

    system_prompt: Optional[str] = None
    assistant_profile: Optional[
        Literal[
            "general",
            "small_business",
            "website_owner",
            "whatsapp_business",
            "instagram_dm",
            "marketing",
            "call_centre",
        ]
    ] = Field(
        default=None,
        description=(
            "Persona profile that keeps replies on the business. Stored in the agent "
            "config; omitted leaves it unchanged."
        ),
    )
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    voice: Optional[str] = Field(default=None, max_length=80)
    language: Optional[str] = Field(default=None, max_length=16)
    greeting: Optional[str] = None
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32000)
    knowledge_base_ids: Optional[list[uuid.UUID]] = Field(
        default=None,
        max_length=100,
        description=(
            "Knowledge bases explicitly bound to this agent. Omitted leaves the "
            "existing binding unchanged."
        ),
    )


class AgentRead(BaseModel):
    """Flat read model — joins Agent + AgentConfig into one shape."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    description: Optional[str] = None
    type: str
    status: str
    model: str
    avatar_url: Optional[str] = None
    website_url: Optional[str] = None

    system_prompt: Optional[str] = None
    temperature: float
    voice: Optional[str] = None
    language: str
    greeting: Optional[str] = None
    max_tokens: int
    knowledge_base_ids: Optional[list[uuid.UUID]] = None

    # Lifecycle: True when the agent meets the minimum requirements to serve
    # traffic (currently: a non-empty system prompt). The UI uses this to warn
    # about incomplete agents and to gate activation.
    is_ready: bool = True

    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentRead]
    total: int
    limit: int
    offset: int
