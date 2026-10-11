"""Webhook schemas (R7 developer platform)."""
from __future__ import annotations

import uuid
import ipaddress
import socket
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebhookEventInfo(BaseModel):
    event: str
    description: str


def validate_public_webhook_url(value: str) -> str:
    """Allow only publicly routable HTTP(S) destinations.

    This validation is repeated by the delivery service immediately before
    every request. That closes the common DNS-rebinding window between endpoint
    registration and delivery; redirects are disabled at the HTTP client.
    Network-level egress restrictions must still be applied by deployment.
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
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        raise ValueError("Private and internal hosts are not allowed")
    try:
        ipaddress.ip_address(host)
        addresses = [host]
    except ValueError:
        try:
            addresses = list({info[4][0] for info in socket.getaddrinfo(host, None)})
        except (OSError, UnicodeError):
            raise ValueError("Webhook hostname could not be resolved") from None
    if not addresses:
        raise ValueError("Webhook hostname could not be resolved")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise ValueError("Private, loopback, reserved, or link-local destinations are not allowed")
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
