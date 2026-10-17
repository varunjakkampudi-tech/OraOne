"""Webhook schemas (R7 developer platform)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.egress_guard import (
    REASON_UNRESOLVABLE,
    UnsafeDestinationError,
    resolve_public_addresses,
)


class WebhookEventInfo(BaseModel):
    event: str
    description: str


def validate_public_webhook_url(value: str) -> str:
    """Allow only publicly routable HTTP(S) destinations.

    This is registration-time validation. The delivery service resolves the
    host again immediately before each request and connects to the validated
    IP (see ``app.services.egress_guard``), which closes the DNS-rebinding
    window between registration and delivery. Redirects are disabled at the
    HTTP client. Network-level egress restrictions must still be applied by
    deployment.
    """
    value = value.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http:// or https://")
    if not parsed.hostname:
        raise ValueError("URL must include a hostname")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("URL credentials and fragments are not allowed")
    host = parsed.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(
        (".local", ".internal")
    ):
        raise ValueError("Private and internal hosts are not allowed")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        resolve_public_addresses(host, port)
    except UnsafeDestinationError as exc:
        if exc.reason == REASON_UNRESOLVABLE:
            raise ValueError("Webhook hostname could not be resolved") from None
        raise ValueError(
            "Private, loopback, reserved, or link-local destinations are not allowed"
        ) from None
    return value


class WebhookCreateRequest(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    events: List[str] = Field(default_factory=list)
    description: Optional[str] = Field(default=None, max_length=255)

    @field_validator("url")
    @classmethod
    def _public_url(cls, v: str) -> str:
        return validate_public_webhook_url(v)


class WebhookUpdateRequest(BaseModel):
    url: Optional[str] = Field(default=None, max_length=2048)
    events: Optional[List[str]] = None
    description: Optional[str] = Field(default=None, max_length=255)
    status: Optional[str] = None

    @field_validator("url")
    @classmethod
    def _public_url(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else validate_public_webhook_url(v)


class WebhookDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: str
    success: bool
    status_code: Optional[int] = None
    attempts: int
    error: Optional[str] = None
    created_at: datetime


class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    description: Optional[str] = None
    status: str
    events: List[str] = Field(default_factory=list)
    failure_count: int
    last_status: Optional[str] = None
    last_delivery_at: Optional[datetime] = None
    created_at: datetime


class WebhookCreateResponse(BaseModel):
    webhook: WebhookOut
    secret: str  # shown once


class WebhookListResponse(BaseModel):
    webhooks: List[WebhookOut]
    events: List[WebhookEventInfo]
