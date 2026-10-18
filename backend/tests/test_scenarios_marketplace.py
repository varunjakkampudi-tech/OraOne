"""Marketplace scenarios: install gating by integration and workflow readiness, the
permission refusal on install, provider setup that is not ready, and per-tenant state.

Integration states are built from fake rows. Nothing is installed, and no provider is called.
"""

from __future__ import annotations

import pytest

from app.api.marketplace import routes as marketplace_routes
from app.core.permissions import Permission
from app.database.models.workflow import StepType
from app.services import marketplace as catalog
from scenario_support import (
    ORG_A,
    ORG_B,
    FakeSession,
    org_app,
    record_permissions,
    sql,
)

CONNECTED = {"google_drive": ("Google Drive", "connected")}
NOT_CONNECTED = {"google_drive": ("Google Drive", "not_connected")}
NEEDS_OAUTH_APP = {"google_drive": ("Google Drive", "requires_account_setup")}


def _integration_listing(provider: str = "google_drive") -> dict:
    return {"category": "integration", "blueprint": {"provider": provider}}


def _workflow_listing(steps: list[str], trigger: str = "event") -> dict:
    return {
        "category": "workflow",
        "blueprint": {"trigger": trigger, "steps": steps},
    }


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
def test_integration_listing_installs_once_its_provider_is_connected():
    evaluation = catalog.evaluate_listing(_integration_listing(), CONNECTED)

    assert evaluation.installable is True
    assert [r.status for r in evaluation.requirements] == ["satisfied"]


@pytest.mark.smoke
def test_workflow_listing_with_supported_steps_creates_a_draft_workflow():
    supported_step = next(t.value for t in StepType)

    evaluation = catalog.evaluate_listing(
        _workflow_listing([supported_step]), CONNECTED
    )

    assert evaluation.installable is True
    assert evaluation.creates_workflow is True


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
def test_integration_listing_is_refused_until_the_provider_is_connected():
    evaluation = catalog.evaluate_listing(_integration_listing(), NOT_CONNECTED)

    assert evaluation.installable is False
    assert evaluation.blocking_messages == [
        "Requires Google Drive. Connect it on the Integrations page first."
    ]


@pytest.mark.critical
def test_workflow_with_an_unsupported_step_is_refused_and_creates_nothing():
    evaluation = catalog.evaluate_listing(
        _workflow_listing(["teleport_to_moon"]), CONNECTED
    )

    assert evaluation.installable is False
    assert evaluation.creates_workflow is False
    assert any("teleport_to_moon" in m for m in evaluation.blocking_messages)


@pytest.mark.critical
def test_viewer_cannot_install_a_listing(monkeypatch):
    recorded: list = []
    record_permissions(monkeypatch, recorded)
    session = FakeSession()
    client = org_app(marketplace_routes.router, role="viewer", session=session)

    response = client.post("/api/marketplace/listings/integration-hubspot/install")

    assert response.status_code == 403
    assert Permission.AGENTS_WRITE in recorded
    assert session.commits == 0
    assert session.added == []


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
def test_provider_whose_oauth_app_is_not_set_up_is_refused_with_an_admin_message():
    evaluation = catalog.evaluate_listing(_integration_listing(), NEEDS_OAUTH_APP)

    assert evaluation.installable is False
    assert evaluation.blocking_messages == [
        "Requires Google Drive. An administrator must set up its OAuth app before it can be connected."
    ]


@pytest.mark.regression
def test_provider_missing_from_the_registry_is_reported_unavailable_not_installed():
    evaluation = catalog.evaluate_listing(_integration_listing("made_up_provider"), {})

    assert evaluation.installable is False
    assert evaluation.requirements[0].status == "unavailable"
    assert "not available yet" in evaluation.blocking_messages[0]


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_connected_providers_are_read_only_for_the_installing_org():
    session = FakeSession(scalars=[["google_drive"]])

    states = await marketplace_routes._integration_states(session, ORG_A)

    assert states["google_drive"][1] == "connected"
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement


@pytest.mark.critical
def test_installed_listings_are_listed_only_for_the_callers_org():
    session = FakeSession(scalars=[[]])
    client = org_app(marketplace_routes.router, role="member", session=session)

    response = client.get("/api/marketplace/installations")

    assert response.status_code == 200
    assert response.json() == []
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement
    assert "installed" in statement
