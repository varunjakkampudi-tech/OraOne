"""Create or refresh the local development accounts.

Two accounts are seeded for local testing:

    varun@oraone.in   regular user        password: varun@oraone.in
    admin@oraone.in   platform owner      password: oraone.in

The script refuses to run outside ``ENVIRONMENT=development``, so these
well-known credentials can never reach a production database. Running it again
is safe: existing accounts get their password, role and status reset to the
values below.

Usage (from the ``backend`` folder, with the local database running):

    python scripts/seed_dev_users.py

Development password sign-in must also be enabled for the login form to work:
set ``ALLOW_DEV_PASSWORD_LOGIN=true`` in ``backend/.env``.

The organizations of these accounts are moved to the Business plan so every
model in the catalogue is available locally. This is a development-only grant:
it does not go through billing. Set ``ORAONE_FREE_ACCESS_ONLY=false`` in
``backend/.env`` so the Free-only guard does not undo it.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.database import session as db  # noqa: E402
from app.database.models.billing import Plan, PlanCode  # noqa: E402
from app.database.models.organization import Organization, OrgPlan  # noqa: E402
from app.database.models.organization_member import OrganizationMember  # noqa: E402
from app.database.models.user import User, UserRole, UserStatus  # noqa: E402
from app.services import billing_service  # noqa: E402

#: Development accounts. Each entry is (email, password, display name, role).
DEV_USERS: tuple[tuple[str, str, str, UserRole], ...] = (
    ("varun@oraone.in", "varun@oraone.in", "Varun", UserRole.user),
    ("admin@oraone.in", "oraone.in", "OraOne Admin", UserRole.super_admin),
)


async def _grant_business_plan(session, user_ids: list[uuid.UUID]) -> None:
    """Put every organization the dev accounts belong to on the Business plan."""
    await billing_service.ensure_plans_seeded(session)
    business = await session.scalar(select(Plan).where(Plan.code == PlanCode.business))
    if business is None:
        raise RuntimeError("Business plan is missing after seeding plans.")
    org_ids = (
        await session.scalars(
            select(OrganizationMember.organization_id).where(
                OrganizationMember.user_id.in_(user_ids)
            )
        )
    ).all()
    for org_id in set(org_ids):
        sub = await billing_service.get_or_create_subscription(session, org_id)
        sub.plan_id = business.id
        org = await session.get(Organization, org_id)
        if org is not None:
            org.plan = OrgPlan.growth
        print(f"organization {org_id} set to business plan")


async def seed() -> None:
    """Upsert each development account with its documented password and role."""
    db.init_engine()
    assert db.AsyncSessionLocal is not None
    async with db.AsyncSessionLocal() as session:
        seeded_ids: list[uuid.UUID] = []
        for email, password, name, role in DEV_USERS:
            user = await session.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(
                    auth_subject=str(uuid.uuid4()),
                    email=email,
                    full_name=name,
                )
                session.add(user)
            user.password_hash = hash_password(password)
            user.full_name = name
            user.role = role
            user.status = UserStatus.active
            user.is_email_verified = True
            await session.flush()
            seeded_ids.append(user.id)
            print(f"seeded {email} ({role.value})")
        await _grant_business_plan(session, seeded_ids)
        await session.commit()
    await db.dispose_engine()


def main() -> int:
    """Entry point. Returns a process exit code."""
    if settings.environment != "development":
        print("Refusing to seed: ENVIRONMENT must be 'development'.", file=sys.stderr)
        return 1
    asyncio.run(seed())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
