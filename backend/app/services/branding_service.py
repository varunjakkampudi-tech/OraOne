"""White-label branding service (Phase 12, Module 15).

Manages per-org brand settings with plan-gated premium controls. Premium
white-label features (hiding the "Powered by" mark, custom domains) require
the ``business`` tier or above; basic theming (name, logo, colours,
support links) is available to everyone.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.model_catalogue import plan_rank
from app.database.models.org_branding import OrgBranding
from app.database.models.organization import Organization
from app.services import billing_service

# Plan tier (rank) at/above which premium white-label unlocks.
WHITE_LABEL_MIN_RANK = plan_rank("business")

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
_DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(?:\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$"
)

DEFAULT_PRIMARY = "#4F46E5"
DEFAULT_ACCENT = "#06B6D4"


async def _plan_code(session: AsyncSession, organization_id: uuid.UUID) -> str:
    sub = await billing_service.get_or_create_subscription(session, organization_id)
    return str(getattr(sub.plan.code, "value", sub.plan.code))


def can_white_label(plan_code: str) -> bool:
    return plan_rank(plan_code) >= WHITE_LABEL_MIN_RANK


async def get_branding(
    session: AsyncSession, organization_id: uuid.UUID
) -> Optional[OrgBranding]:
    return await session.scalar(
        select(OrgBranding).where(
            OrgBranding.organization_id == organization_id
        )
    )


async def get_or_create_branding(
    session: AsyncSession, organization_id: uuid.UUID
) -> OrgBranding:
    branding = await get_branding(session, organization_id)
    if branding is not None:
        return branding
    branding = OrgBranding(
        organization_id=organization_id,
        primary_color=DEFAULT_PRIMARY,
        accent_color=DEFAULT_ACCENT,
    )
    session.add(branding)
    await session.commit()
    await session.refresh(branding)
    return branding


def _norm_hex(value: str, field: str) -> str:
    v = (value or "").strip()
    if not _HEX_RE.match(v):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be a hex colour like #4F46E5.",
        )
    return v


async def branding_view(
    session: AsyncSession, organization_id: uuid.UUID
) -> dict:
    plan_code = await _plan_code(session, organization_id)
    branding = await get_or_create_branding(session, organization_id)
    org = await session.get(Organization, organization_id)
    return {
        "plan_code": plan_code,
        "white_label_enabled": can_white_label(plan_code),
        "organization_name": org.name if org else None,
        "brand_name": branding.brand_name,
        "logo_url": branding.logo_url,
        "icon_url": branding.icon_url,
        "primary_color": branding.primary_color,
        "accent_color": branding.accent_color,
        "support_email": branding.support_email,
        "support_url": branding.support_url,
        "custom_domain": branding.custom_domain,
        "hide_powered_by": branding.hide_powered_by,
    }


async def update_branding(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    brand_name: Optional[str],
    logo_url: Optional[str],
    icon_url: Optional[str],
    primary_color: str,
    accent_color: str,
    support_email: Optional[str],
    support_url: Optional[str],
    custom_domain: Optional[str],
    hide_powered_by: bool,
) -> OrgBranding:
    plan_code = await _plan_code(session, organization_id)
    premium = can_white_label(plan_code)

    primary = _norm_hex(primary_color, "Primary colour")
    accent = _norm_hex(accent_color, "Accent colour")

    domain = (custom_domain or "").strip().lower() or None
    if domain is not None:
        if not premium:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Custom domains require the Business plan or higher.",
            )
        if not _DOMAIN_RE.match(domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Enter a valid domain like brand.example.com.",
            )

    if hide_powered_by and not premium:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Hiding the 'Powered by' mark requires the Business plan or higher.",
        )

    branding = await get_or_create_branding(session, organization_id)
    branding.brand_name = (brand_name or "").strip() or None
    branding.logo_url = (logo_url or "").strip() or None
    branding.icon_url = (icon_url or "").strip() or None
    branding.primary_color = primary
    branding.accent_color = accent
    branding.support_email = (support_email or "").strip() or None
    branding.support_url = (support_url or "").strip() or None
    branding.custom_domain = domain
    branding.hide_powered_by = bool(hide_powered_by) and premium
    await session.commit()
    await session.refresh(branding)
    return branding


async def set_branding_asset(
    session: AsyncSession,
    organization_id: uuid.UUID,
    *,
    field: str,
    url: Optional[str],
) -> OrgBranding:
    """Set just the logo or icon URL (used by the upload endpoints)."""
    branding = await get_or_create_branding(session, organization_id)
    if field == "logo":
        branding.logo_url = url
    elif field == "icon":
        branding.icon_url = url
    else:  # pragma: no cover - guarded by caller
        raise ValueError(f"Unknown branding asset field: {field!r}")
    await session.commit()
    await session.refresh(branding)
    return branding


async def public_branding(
    session: AsyncSession, *, org_ref: str
) -> Optional[dict]:
    """Resolve public-safe branding by org slug or UUID (no auth).

    Used to white-label customer-facing surfaces before a user signs in.
    """
    org: Optional[Organization] = None
    try:
        org_id = uuid.UUID(org_ref)
        org = await session.get(Organization, org_id)
    except (ValueError, TypeError):
        org = await session.scalar(
            select(Organization).where(Organization.slug == org_ref)
        )
    if org is None or org.deleted_at is not None:
        return None

    branding = await get_branding(session, org.id)
    return {
        "organization_name": org.name,
        "brand_name": (branding.brand_name if branding else None) or org.name,
        "logo_url": branding.logo_url if branding else None,
        "icon_url": branding.icon_url if branding else None,
        "primary_color": branding.primary_color if branding else DEFAULT_PRIMARY,
        "accent_color": branding.accent_color if branding else DEFAULT_ACCENT,
        "support_email": branding.support_email if branding else None,
        "support_url": branding.support_url if branding else None,
        "hide_powered_by": bool(branding.hide_powered_by) if branding else False,
    }
