"""IdentityService — the bridge between Cognito (auth-of-record) and our
Postgres `users` + `organizations` + `organization_members` triad.

`upsert_from_cognito` is meant to be called once on every successful
login: it finds-or-creates the user, and on first-touch also auto-creates
a personal organisation with the user as owner.
"""
from __future__ import annotations

import re
from typing import NamedTuple, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.organization import Organization, OrgPlan
from app.database.models.organization_member import (
    MemberRole,
    OrganizationMember,
)
from app.database.models.project import Project, ProjectStatus
from app.database.models.user import User
from app.database.repositories.organization_member_repository import (
    OrganizationMemberRepository,
)
from app.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.database.repositories.user_repository import UserRepository


class IdentityResult(NamedTuple):
    user: User
    organization: Organization
    membership: OrganizationMember
    is_new_user: bool


# Matches a Cognito UUID-shaped string so we can refuse to use it as a display name.
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _derive_workspace_display(
    *, full_name: Optional[str], given_name: Optional[str], email: str
) -> str:
    """First-name-only display used for the auto-created personal workspace.

    Priority:
      1. First whitespace-separated token of ``full_name``  ("John Doe" → "John")
      2. ``given_name``
      3. Email local-part, title-cased                       ("varun@x.com" → "Varun")

    Anything UUID-shaped (e.g. an accidentally-leaked Cognito sub) is rejected
    at every step and we fall through to the next candidate.
    """
    def _clean(candidate: Optional[str]) -> Optional[str]:
        if not candidate:
            return None
        c = candidate.strip()
        if not c or _UUID_RE.match(c):
            return None
        return c

    fn = _clean(full_name)
    if fn:
        first_token = fn.split()[0]
        cleaned = _clean(first_token)
        if cleaned:
            return cleaned[:1].upper() + cleaned[1:]

    gn = _clean(given_name)
    if gn:
        return gn[:1].upper() + gn[1:]

    local = email.split("@", 1)[0] if "@" in email else ""
    local = _clean(local) or "My"
    return local[:1].upper() + local[1:]


class IdentityService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.orgs = OrganizationRepository(session)
        self.members = OrganizationMemberRepository(session)

    async def upsert_from_cognito(
        self,
        *,
        cognito_sub: str,
        email: str,
        full_name: Optional[str] = None,
        given_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> IdentityResult:
        """Idempotent identity hydration on Cognito login.

        First call: creates the User + a personal Organization + an Owner
        OrganizationMember row.
        Subsequent calls: returns the existing triple, refreshing
        `last_login_at` and any newly-supplied profile fields.

        Organization names are derived **only** for newly-created orgs from,
        in order: first token of ``full_name`` → ``given_name`` → email
        local-part. Existing org names are never touched here.
        """
        existing = await self.users.get_by_cognito_sub(cognito_sub)
        is_new_user = existing is None

        user = await self.users.upsert_from_cognito(
            cognito_sub=cognito_sub,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
        )

        orgs = await self.orgs.list_for_user(user.id)
        if orgs:
            organization = orgs[0]
            # Self-heal: migrate the legacy auto-generated personal workspace
            # name "<Name> Workspace" → "<Name>'s Workspace".
            display = _derive_workspace_display(
                full_name=full_name,
                given_name=given_name,
                email=email,
            )
            if organization.name == f"{display} Workspace":
                organization.name = f"{display}'s Workspace"
        else:
            display = _derive_workspace_display(
                full_name=full_name,
                given_name=given_name,
                email=email,
            )
            slug = await self.orgs.ensure_unique_slug(f"{display}-workspace")
            organization = Organization(
                name=f"{display}'s Workspace",
                slug=slug,
                plan=OrgPlan.free,
                owner_user_id=user.id,
            )
            self.session.add(organization)
            await self.session.flush()

            # Every org needs at least one project. Seed the first one as
            # "First Project" (not "Default") so the UI reads as intentional
            # and brand-polished rather than unfinished.
            self.session.add(
                Project(
                    organization_id=organization.id,
                    name="First Project",
                    slug="first-project",
                    is_default=True,
                    status=ProjectStatus.active,
                    created_by_user_id=user.id,
                )
            )
            await self.session.flush()

        membership = await self.members.ensure_membership(
            organization_id=organization.id,
            user_id=user.id,
            role=MemberRole.owner if organization.owner_user_id == user.id else MemberRole.member,
        )

        return IdentityResult(
            user=user,
            organization=organization,
            membership=membership,
            is_new_user=is_new_user,
        )
