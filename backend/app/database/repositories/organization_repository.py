"""Organization repository."""
from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select

from app.database.models.organization import Organization
from app.database.repositories.base import BaseRepository


def slugify(value: str) -> str:
    """Crude but deterministic slug — replace runs of non-alphanum with '-'."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip()).strip("-").lower()
    return s or "org"


class OrganizationRepository(BaseRepository[Organization]):
    model = Organization

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        return await self.session.scalar(
            select(Organization).where(Organization.slug == slug.lower())
        )

    async def list_for_user(self, user_id: uuid.UUID) -> list[Organization]:
        """All orgs the user is a member of."""
        from app.database.models.organization_member import OrganizationMember  # local

        q = (
            select(Organization)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(OrganizationMember.user_id == user_id)
            .where(Organization.deleted_at.is_(None))
        )
        return list((await self.session.scalars(q)).all())

    async def ensure_unique_slug(self, base: str) -> str:
        """Return `base` if free, else `base-2`, `base-3`, …"""
        slug = slugify(base)
        candidate = slug
        n = 2
        while await self.get_by_slug(candidate) is not None:
            candidate = f"{slug}-{n}"
            n += 1
        return candidate
