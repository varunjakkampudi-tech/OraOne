"""White-label branding schemas (Phase 12, Module 15)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class BrandingView(BaseModel):
    plan_code: str
    white_label_enabled: bool
    organization_name: Optional[str] = None
    brand_name: Optional[str] = None
    logo_url: Optional[str] = None
    icon_url: Optional[str] = None
    primary_color: str
    accent_color: str
    support_email: Optional[str] = None
    support_url: Optional[str] = None
    custom_domain: Optional[str] = None
    hide_powered_by: bool


class BrandingUpdate(BaseModel):
    brand_name: Optional[str] = Field(None, max_length=120)
    logo_url: Optional[str] = Field(None, max_length=500)
    icon_url: Optional[str] = Field(None, max_length=500)
    primary_color: str = Field(..., max_length=9)
    accent_color: str = Field(..., max_length=9)
    support_email: Optional[str] = Field(None, max_length=160)
    support_url: Optional[str] = Field(None, max_length=500)
    custom_domain: Optional[str] = Field(None, max_length=255)
    hide_powered_by: bool = False


class PublicBranding(BaseModel):
    organization_name: str
    brand_name: str
    logo_url: Optional[str] = None
    icon_url: Optional[str] = None
    primary_color: str
    accent_color: str
    support_email: Optional[str] = None
    support_url: Optional[str] = None
    hide_powered_by: bool
