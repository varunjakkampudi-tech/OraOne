"""Marketplace: listing lookup, install idempotency, uninstall and review ownership.

Complements test_marketplace_install_gating.py (capability gating and blueprint installs). The
route functions are called directly with an in-memory session; nothing touches a database.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.dialects import postgresql

from app.api.marketplace import routes
from app.database.models.marketplace import InstallStatus
from app.database.models.marketplace_review import MarketplaceReview
from app.middleware.org_context import OrgContext
from app.middleware.project_context import ProjectContext
from app.services import marketplace as catalog

ORG = uuid.uuid4()
OTHER_ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()
REAL_SLUG = catalog.list_listings()[0]["slug"]


class _Result:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, *, scalar=()):
        self._scalar = list(scalar)
        self.statements = []
        self.added = []
        self.deleted = []
        self.committed = 0

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self._scalar.pop(0) if self._scalar else None

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Result([])

    async def execute(self, stmt):
        self.statements.append(stmt)
        return _Result([])

    async def get(self, model, pk):
        return None

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        self.committed += 1

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = "2026-10-17T12:00:00Z"


def _pctx(org=ORG):
    return ProjectContext(
        user_id=USER,
        organization_id=org,
        membership_role="admin",
        project_id=PROJECT,
        project_slug="default",
        is_default_project=True,
    )


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


@pytest.fixture(autouse=True)
def _no_audit(monkeypatch):
    monkeypatch.setattr(routes, "audit", lambda *a, **k: None)


def test_unknown_listing_is_not_found():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.get_listing(
                "does-not-exist",
                ctx=OrgContext(USER, "s", ORG, "admin"),
                db=FakeSession(),
            )
        )
    assert exc.value.status_code == 404


def test_installing_an_unknown_listing_is_not_found_and_creates_nothing():
    session = FakeSession()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.install_listing("does-not-exist", pctx=_pctx(), db=session))
    assert exc.value.status_code == 404
    assert session.added == []


def test_installing_twice_returns_the_existing_installation_without_creating_another(
    monkeypatch,
):
    slug = "synthetic-existing"
    monkeypatch.setattr(
        catalog,
        "get_listing",
        lambda s: (
            {
                "slug": slug,
                "name": "Existing",
                "category": "workflow",
                "blueprint": {"trigger": "manual", "steps": []},
            }
            if s == slug
            else None
        ),
    )
    existing = SimpleNamespace(
        id=uuid.uuid4(),
        listing_slug=slug,
        listing_name="Existing",
        category="workflow",
        status=InstallStatus.installed,
        agent_id=None,
        created_at="2026-10-01T00:00:00Z",
    )
    session = FakeSession(scalar=[existing])

    response = asyncio.run(routes.install_listing(slug, pctx=_pctx(), db=session))

    assert response.installation.id == existing.id
    assert session.added == []
    assert session.committed == 0


def test_uninstall_is_scoped_to_the_callers_organization():
    session = FakeSession(scalar=[None])  # another organization's row is invisible
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.uninstall_listing(
                uuid.uuid4(), ctx=OrgContext(USER, "s", ORG, "admin"), db=session
            )
        )
    assert exc.value.status_code == 404
    assert str(ORG) in _sql(session.statements[0])
    assert session.committed == 0


def test_uninstall_marks_the_callers_installation_removed():
    row = SimpleNamespace(
        id=uuid.uuid4(), listing_slug="workflow-x", status=InstallStatus.installed
    )
    session = FakeSession(scalar=[row])

    response = asyncio.run(
        routes.uninstall_listing(
            row.id, ctx=OrgContext(USER, "s", ORG, "admin"), db=session
        )
    )

    assert response.status_code == 204
    assert row.status == InstallStatus.removed
    assert session.committed == 1


def test_review_is_created_once_then_updated_in_place():
    slug = REAL_SLUG
    session = FakeSession(scalar=[None])
    ctx = OrgContext(USER, "s", ORG, "member")

    created = asyncio.run(
        routes.upsert_review(
            slug,
            routes.ReviewCreate(rating=4, title="Good", body="Works"),
            ctx=ctx,
            db=session,
        )
    )
    assert created.rating == 4
    assert created.is_mine is True
    reviews = [o for o in session.added if isinstance(o, MarketplaceReview)]
    assert len(reviews) == 1

    existing = reviews[0]
    session2 = FakeSession(scalar=[existing])
    updated = asyncio.run(
        routes.upsert_review(
            slug, routes.ReviewCreate(rating=2, title="Changed"), ctx=ctx, db=session2
        )
    )
    assert updated.rating == 2
    assert updated.title == "Changed"
    assert session2.added == []  # no second review row


def test_review_for_an_unknown_listing_is_not_found():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.upsert_review(
                "no-such-listing",
                routes.ReviewCreate(rating=5),
                ctx=OrgContext(USER, "s", ORG, "member"),
                db=FakeSession(),
            )
        )
    assert exc.value.status_code == 404


@pytest.mark.parametrize("rating", [0, 6, -1])
def test_review_rating_must_be_between_one_and_five(rating):
    with pytest.raises(ValidationError):
        routes.ReviewCreate(rating=rating)


def test_deleting_a_review_removes_only_the_callers_own_review():
    session = FakeSession(scalar=[None])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.delete_review(
                REAL_SLUG, ctx=OrgContext(USER, "s", ORG, "member"), db=session
            )
        )
    assert exc.value.status_code == 404
    assert session.deleted == []
    assert str(USER) in _sql(session.statements[0])


def test_deleting_own_review_deletes_it():
    review = SimpleNamespace(id=uuid.uuid4(), user_id=USER, listing_slug=REAL_SLUG)
    session = FakeSession(scalar=[review])

    response = asyncio.run(
        routes.delete_review(
            REAL_SLUG, ctx=OrgContext(USER, "s", ORG, "member"), db=session
        )
    )

    assert response.status_code == 204
    assert session.deleted == [review]
    assert session.committed == 1


def test_installed_listings_shown_to_a_caller_are_only_their_organizations_active_installs():
    session = FakeSession()
    asyncio.run(routes._installed_slugs(session, ORG))
    sql = _sql(session.statements[0])
    assert str(ORG) in sql
    assert str(OTHER_ORG) not in sql
    assert "installed" in sql
