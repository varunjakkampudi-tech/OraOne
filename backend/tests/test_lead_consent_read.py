"""Lead consent provenance is visible on reads and cannot be written through the API.

No database and no network. The read model is built from real ``Lead`` rows, the import
path runs ``save_valid_rows`` against a capturing session, and PATCH runs through a
TestClient with a scripted session and the real RBAC matrix.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.leads import routes as leads_routes
from app.database.models.lead import Lead, LeadStatus, LeadTemperature
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.schemas.leads import LeadRead
from app.services import authorization as authz
from app.services import lead_import_service as svc

ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()
NOW = datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc)


def _lead(extra: dict | None) -> Lead:
    return Lead(
        id=uuid.uuid4(),
        organization_id=ORG,
        project_id=PROJECT,
        name="Ada",
        email="ada@example.com",
        source="import",
        status=LeadStatus.new,
        temperature=LeadTemperature.cold,
        score=10,
        extra=extra,
        created_at=NOW,
        updated_at=NOW,
    )


class _CapturingSession:
    """Collects the leads an import would save. Nothing reaches a database."""

    def __init__(self) -> None:
        self.added: list[Lead] = []

    def add_all(self, objs) -> None:
        self.added.extend(objs)

    async def flush(self) -> None:
        return None


class _PatchSession:
    """Scripted session for PATCH: ``scalar`` returns the one lead, commits are counted."""

    def __init__(self, lead: Lead) -> None:
        self._lead = lead
        self.commits = 0

    async def scalar(self, _stmt):
        return self._lead

    def add(self, _obj):
        pass

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _obj) -> None:
        return None


def _patch_client(lead: Lead, role: str = "member") -> tuple[TestClient, _PatchSession]:
    session = _PatchSession(lead)

    async def _org() -> OrgContext:
        return OrgContext(
            user_id=USER, auth_subject="sub", organization_id=ORG, membership_role=role
        )

    async def _project() -> ProjectContext:
        return ProjectContext(
            user_id=USER,
            organization_id=ORG,
            membership_role=role,
            project_id=PROJECT,
            project_slug="default",
            is_default_project=True,
        )

    app = FastAPI()
    app.include_router(leads_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: session
    return TestClient(app), session


@pytest.fixture
def allow_rbac(monkeypatch):
    """Use the real role matrix, without the subscription lookups."""
    from app.core.permissions import has_permission

    async def authorize(session, ctx, *, permission=None, **_):
        if permission and not has_permission(ctx.membership_role, permission):
            raise HTTPException(
                403, f"Role '{ctx.membership_role}' lacks {permission}."
            )
        return SimpleNamespace(raise_for_denied=lambda: None)

    monkeypatch.setattr(authz, "authorize", authorize)


# ───────────────────────── read model ─────────────────────────


def _parsed_import(csv_text: str):
    return svc.prepare_import(csv_text.encode("utf-8"), "contacts.csv")


@pytest.mark.asyncio
async def test_imported_lead_exposes_import_consent_source_and_note(monkeypatch):
    parsed = _parsed_import("Name,Email,Consent\nAda Lovelace,ada@example.com,yes\n")

    async def _no_triggers(*_args, **_kwargs):
        return None

    monkeypatch.setattr(svc.workflow_triggers, "fire_lead_created", _no_triggers)
    session = _CapturingSession()
    await svc.save_valid_rows(
        session,
        organization_id=ORG,
        project_id=PROJECT,
        user_id=USER,
        parsed=parsed,
    )
    assert len(session.added) == 1
    imported = session.added[0]
    # The database fills id and timestamps on flush; set them as a flush would.
    imported.id = uuid.uuid4()
    imported.created_at = NOW
    imported.updated_at = NOW

    read = leads_routes._to_read(imported)

    assert read.consent == "granted"
    assert read.consent_source == "import_csv"
    assert read.consent_note == svc.IMPORTED_CONSENT_NOTE
    assert isinstance(read.consent_recorded_at, datetime)

    body = read.model_dump(mode="json")
    # Only the four consent fields are added. The import bookkeeping stays internal.
    assert "import" not in body
    assert "extra" not in body


def test_manual_lead_returns_no_import_source():
    read = leads_routes._to_read(_lead({"tags": ["vip"]}))

    assert read.consent is None
    assert read.consent_source is None
    assert read.consent_note is None
    assert read.consent_recorded_at is None
    assert read.tags == ["vip"]


def test_manual_lead_with_no_extra_returns_no_consent():
    read = leads_routes._to_read(_lead(None))

    assert read.consent_source is None
    assert read.consent_note is None


def test_unrelated_extra_keys_are_not_exposed():
    read = leads_routes._to_read(
        _lead(
            {
                "notes": "call back",
                "import": {"upload_id": "u1", "row": 2},
                "secret": "x",
            }
        )
    )

    dumped = read.model_dump()
    assert "import" not in dumped
    assert "secret" not in dumped
    assert "upload_id" not in str(dumped)
    assert read.notes == "call back"


def test_malformed_recorded_at_is_dropped_not_fatal():
    read = leads_routes._to_read(
        _lead({"consent_source": "import_csv", "consent_recorded_at": "not-a-date"})
    )

    assert read.consent_source == "import_csv"
    assert read.consent_recorded_at is None


def test_read_schema_defaults_leave_consent_empty():
    fields = LeadRead.model_fields
    for name in ("consent", "consent_source", "consent_note", "consent_recorded_at"):
        assert fields[name].default is None


# ───────────────────────── not writable ─────────────────────────


def test_patch_cannot_write_consent_fields(allow_rbac):
    original_extra = {"consent": "unknown"}
    lead = _lead(dict(original_extra))
    client, session = _patch_client(lead, role="member")

    response = client.patch(
        f"/api/leads/{lead.id}",
        json={
            "consent": "granted",
            "consent_source": "import_csv",
            "consent_note": "Imported consent, confirm the source",
            "consent_recorded_at": NOW.isoformat(),
            "extra": {"consent": "granted", "consent_source": "import_csv"},
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["consent_source"] is None
    assert body["consent_note"] is None
    assert body["consent_recorded_at"] is None
    assert body["consent"] == "unknown"  # the stored value is unchanged
    assert lead.extra == original_extra
    assert "consent_source" not in lead.extra
    assert session.commits == 1


def test_patch_request_model_has_no_consent_fields():
    from app.schemas.leads import LeadUpdate

    for name in ("consent", "consent_source", "consent_note", "consent_recorded_at"):
        assert name not in LeadUpdate.model_fields
