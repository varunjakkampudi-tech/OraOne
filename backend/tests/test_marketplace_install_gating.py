"""Marketplace installs are gated on real capability (no network, no database).

The route-level test drives ``install_listing`` with an in-memory fake session.
"""

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.marketplace import routes
from app.database.models.workflow import StepType, WorkflowTrigger
from app.services import marketplace as catalog

CONNECTED = {
    "google_drive": ("Google Drive", "connected"),
    "hubspot": ("HubSpot CRM", "planned"),
}
NOT_CONNECTED = {
    "google_drive": ("Google Drive", "not_connected"),
    "hubspot": ("HubSpot CRM", "planned"),
}


def _listing(slug):
    item = catalog.get_listing(slug)
    assert item is not None, slug
    return item


def test_workflow_engine_enums_are_the_source_of_truth():
    assert "event" in catalog.SUPPORTED_WORKFLOW_TRIGGERS
    assert "delay" in catalog.SUPPORTED_WORKFLOW_STEPS
    assert "wait_1h" not in catalog.SUPPORTED_WORKFLOW_STEPS
    assert "lead.created" not in catalog.SUPPORTED_WORKFLOW_TRIGGERS
    assert {t.value for t in WorkflowTrigger} == catalog.SUPPORTED_WORKFLOW_TRIGGERS
    assert {t.value for t in StepType} == catalog.SUPPORTED_WORKFLOW_STEPS


def test_shipped_lead_followup_blueprint_is_not_installable_and_says_why():
    ev = catalog.evaluate_listing(_listing("workflow-lead-followup"), CONNECTED)
    assert ev.installable is False
    assert ev.creates_workflow is False
    messages = " ".join(ev.blocking_messages)
    assert "'lead.created' trigger" in messages
    assert "'wait_1h' step" in messages
    assert "'email' step" in messages


def test_integration_listing_requires_a_live_connection():
    ev = catalog.evaluate_listing(_listing("integration-hubspot"), CONNECTED)
    assert ev.installable is False
    [req] = ev.requirements
    assert req.status == catalog.REQ_UNAVAILABLE
    assert req.message == "Requires HubSpot CRM, which is not available yet."


def test_integration_listing_installable_only_when_connected():
    item = {
        "slug": "synthetic-drive",
        "category": "integration",
        "blueprint": {"provider": "google_drive"},
    }
    assert catalog.evaluate_listing(item, NOT_CONNECTED).installable is False
    ev = catalog.evaluate_listing(item, CONNECTED)
    assert ev.installable is True
    assert ev.requirements[0].status == catalog.REQ_SATISFIED


def test_unknown_provider_is_treated_as_unavailable_not_connected():
    item = {
        "slug": "integration-google-calendar",
        "category": "integration",
        "blueprint": {"provider": "google_calendar"},
    }
    ev = catalog.evaluate_listing(item, {})
    assert ev.installable is False
    assert ev.requirements[0].label == "Google Calendar"
    assert ev.requirements[0].status == catalog.REQ_UNAVAILABLE


def test_supported_workflow_blueprint_creates_a_draft_workflow():
    item = {
        "slug": "synthetic-workflow",
        "category": "workflow",
        "blueprint": {"trigger": "manual", "steps": ["transform", "notification"]},
    }
    ev = catalog.evaluate_listing(item, {})
    assert ev.installable is True
    assert ev.creates_workflow is True


def test_agent_template_installs_but_reports_unsupported_automation_and_integrations():
    ev = catalog.evaluate_listing(_listing("dental-clinic-ai"), NOT_CONNECTED)
    assert ev.installable is True
    assert ev.blocking_messages == []
    workflow = [r for r in ev.requirements if r.kind == "workflow"]
    assert workflow and all(r.status == catalog.REQ_UNSUPPORTED for r in workflow)
    assert all(r.blocking is False for r in ev.requirements)
    assert any(r.key == "hubspot" for r in ev.requirements)


def test_every_shipped_listing_evaluates_without_error():
    for item in catalog.LISTINGS:
        ev = catalog.evaluate_listing(item, NOT_CONNECTED)
        assert isinstance(ev.installable, bool)


# ───────────────────────── route-level (fake session) ─────────────────────────


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeSession:
    def __init__(self, connected_providers=()):
        self.connected = list(connected_providers)
        self.added: list[object] = []
        self.committed = False

    async def scalar(self, _stmt):
        return None  # no existing installation

    async def scalars(self, _stmt):
        return _Result(self.connected)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = "2026-01-01T00:00:00Z"


def _pctx():
    return SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )


@pytest.fixture(autouse=True)
def _no_audit(monkeypatch):
    monkeypatch.setattr(routes, "audit", lambda *a, **k: None)


def test_install_of_unconnected_integration_is_refused_with_requires_message():
    session = FakeSession()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.install_listing("integration-hubspot", pctx=_pctx(), db=session)
        )
    assert exc.value.status_code == 409
    # HubSpot is a real OAuth provider now. Without its OAuth app it needs account setup.
    assert exc.value.detail == (
        "Requires HubSpot. An administrator must set up its OAuth app before it can be connected."
    )
    assert session.added == []
    assert session.committed is False


def test_install_of_shipped_workflow_is_refused_and_creates_nothing():
    session = FakeSession()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.install_listing("workflow-lead-followup", pctx=_pctx(), db=session)
        )
    assert exc.value.status_code == 409
    assert "lead.created" in exc.value.detail
    assert session.added == []


def test_install_of_supported_workflow_creates_draft_workflow_with_steps(monkeypatch):
    slug = "synthetic-supported-workflow"
    item = {
        "slug": slug,
        "name": "Synthetic",
        "category": "workflow",
        "summary": "Test blueprint",
        "icon": "x",
        "tags": [],
        "author": "OraOne",
        "featured": False,
        "blueprint": {"trigger": "manual", "steps": ["transform", "notification"]},
    }
    monkeypatch.setattr(catalog, "get_listing", lambda s: item if s == slug else None)
    session = FakeSession()
    response = asyncio.run(routes.install_listing(slug, pctx=_pctx(), db=session))

    from app.database.models.workflow import Workflow, WorkflowStatus, WorkflowStep

    workflows = [o for o in session.added if isinstance(o, Workflow)]
    steps = [o for o in session.added if isinstance(o, WorkflowStep)]
    assert len(workflows) == 1
    assert workflows[0].status == WorkflowStatus.draft
    assert workflows[0].trigger_type == WorkflowTrigger.manual
    assert [s.type for s in steps] == [StepType.transform, StepType.notification]
    assert response.workflow_id == workflows[0].id
    assert session.committed is True


def test_install_of_connected_integration_records_installation_only(monkeypatch):
    slug = "synthetic-drive"
    item = {
        "slug": slug,
        "name": "Drive blueprint",
        "category": "integration",
        "summary": "Test",
        "icon": "x",
        "tags": [],
        "author": "OraOne",
        "featured": False,
        "blueprint": {"provider": "google_drive"},
    }
    monkeypatch.setattr(catalog, "get_listing", lambda s: item if s == slug else None)
    session = FakeSession(connected_providers=["google_drive"])
    response = asyncio.run(routes.install_listing(slug, pctx=_pctx(), db=session))
    assert response.workflow_id is None
    assert response.requirements[0].status == catalog.REQ_SATISFIED
    assert session.committed is True
