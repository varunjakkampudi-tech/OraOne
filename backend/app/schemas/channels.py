"""Pydantic schemas for the Channels & Deploy API (Universal Agent)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChannelRead(BaseModel):
    channel: str
    label: str
    description: str
    icon: str
    enabled: bool
    status: str
    embeddable: bool
    phone_number: Optional[str] = None
    provider: Optional[str] = None
    configuration: dict[str, Any] = Field(default_factory=dict)


class ChannelsResponse(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    items: list[ChannelRead]


class ChannelUpdate(BaseModel):
    enabled: Optional[bool] = None
    status: Optional[str] = None
    phone_number: Optional[str] = Field(default=None, max_length=32)
    provider: Optional[str] = Field(default=None, max_length=40)
    configuration: Optional[dict[str, Any]] = None


class SnippetSet(BaseModel):
    one_line: str
    sdk: str
    npm_install: str
    npm_import: str


class SdkMethod(BaseModel):
    name: str
    description: str


class InstallGuide(BaseModel):
    platform: str
    label: str
    language: str
    code: str


class TriggerSnippet(BaseModel):
    name: str
    language: str
    code: str


class Verification(BaseModel):
    installed: bool
    events_count: int
    loads_count: int
    last_seen: Optional[datetime] = None


class DeployInfo(BaseModel):
    agent_id: uuid.UUID
    agent_name: str
    public_key: str
    widget_id: uuid.UUID
    widget_status: str
    deploy_status: str
    cdn_base: str
    api_base: str
    snippets: SnippetSet
    sdk_methods: list[SdkMethod]
    install_guides: list[InstallGuide]
    trigger_snippets: list[TriggerSnippet]
    domains: list[str]
    verification: Verification
    theme: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)


class DomainsUpdate(BaseModel):
    domains: list[str] = Field(default_factory=list)


class DomainsResponse(BaseModel):
    domains: list[str]


class PublishRequest(BaseModel):
    publish: bool = True
