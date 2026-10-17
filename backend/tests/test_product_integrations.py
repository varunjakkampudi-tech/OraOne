"""Integrations: provider catalog and setup states, connector lookup, and org-scoped routes.

Complements test_integrations_setup_status.py and test_integration_connection_mode.py. No
provider is contacted; connector disconnects are replaced with recorders.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.integrations import routes as int_routes
from app.connectors import registry
from app.connectors.base import BaseConnector, ConnectorError
from app.database.models.integration import (
    ConnectionType,
    IntegrationStatus,
    IntegrationType,
    SyncSchedule,
)
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project

ORG = uuid.uuid4()
OTHER_ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()
CATEGORIES = {
    registry.CATEGORY_COMMUNICATION,
    registry.CATEGORY_DOCUMENTS,
    registry.CATEGORY_DOCUMENTATION,
    registry.CATEGORY_DEVELOPMENT,
    registry.CATEGORY_CRM,
}


# ── registry ─────────────────────────────────────────────────────────────────


def test_every_catalog_entry_is_keyed_by_its_provider_and_uses_a_known_category():
    for key, spec in registry.PROVIDER_CATALOG.items():
        assert key == spec.provider
        assert spec.category in CATEGORIES
        assert spec.auth in ("oauth", "api_key", "webhook")


def test_every_provider_has_a_connector_class_that_implements_the_base_connector():
    for spec in registry.list_specs():
        assert issubclass(spec.connector_cls, BaseConnector), spec.provider


@pytest.mark.parametrize(
    "spec_kwargs, connected, configured, expected",
    [
        ({"available": False}, False, False, registry.SETUP_PLANNED),
        ({"available": False}, True, True, registry.SETUP_CONNECTED),
        (
            {"available": True, "auth": "oauth"},
            False,
            False,
            registry.SETUP_REQUIRES_ACCOUNT_SETUP,
        ),
        (
            {"available": True, "auth": "oauth"},
            False,
            True,
            registry.SETUP_NOT_CONNECTED,
        ),
        (
            {"available": True, "auth": "api_key"},
            False,
            False,
            registry.SETUP_NOT_CONNECTED,
        ),
        ({"available": True, "auth": "oauth"}, True, False, registry.SETUP_CONNECTED),
    ],
)
def test_setup_status_is_derived_from_real_state_only(
    spec_kwargs, connected, configured, expected
):
    spec = registry.ProviderSpec(
        provider="p",
        name="P",
        category=registry.CATEGORY_CRM,
        type=None,
        connector_cls=BaseConnector,
        **spec_kwargs,
    )
    assert (
        registry.provider_setup_status(
            spec, connected=connected, oauth_configured=configured
        )
        == expected
    )


def test_planned_provider_is_never_reported_connected_without_a_live_row():
    planned = registry.get_spec("salesforce")
    assert planned.available is False
    assert (
        registry.provider_setup_status(planned, connected=False, oauth_configured=True)
        == registry.SETUP_PLANNED
    )


def test_unknown_provider_is_refused_on_both_connector_lookups():
    with pytest.raises(KeyError):
        registry.get_connector_for_provider("myspace")
    with pytest.raises(KeyError):
        registry.get_connector(SimpleNamespace(provider="myspace"))


def test_connector_for_a_provider_is_created_without_a_stored_row():
    connector = registry.get_connector_for_provider("google_drive")
    assert isinstance(connector, BaseConnector)
    assert connector.integration is None


# ── routes ───────────────────────────────────────────────────────────────────


class _Rows:
    def __init__(self, items):
        self._items = list(items)

    def all(self):
        return list(self._items)


class FakeSession:
    def __init__(self, *, scalar=(), scalars=()):
        self._scalar = list(scalar)
        self._scalars = list(scalars)
        self.statements = []
        self.executed = []
        self.commits = 0

    async def scalar(self, stmt):
        self.statements.append(stmt)
        return self._scalar.pop(0) if self._scalar else None

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Rows(self._scalars.pop(0) if self._scalars else [])

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _Rows([])

    async def commit(self):
        self.commits += 1

    async def refresh(self, obj):
        return None


def _sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )


def _row(**overrides):
    base = dict(
        id=uuid.uuid4(),
        organization_id=ORG,
        provider="google_drive",
        type=IntegrationType.storage,
        connection_type=ConnectionType.oauth,
        sync_schedule=SyncSchedule.manual,
        created_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        status=IntegrationStatus.connected,
        access_token="ya29.secret-access",
        refresh_token="1//secret-refresh",
        token_expires_at=datetime(2026, 12, 1, tzinfo=timezone.utc),
        external_account="owner@example.test",
        last_error="previous failure",
        deleted_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(int_routes, "audit", lambda *a, **k: None)
    state = SimpleNamespace(role="admin", org=ORG, session=FakeSession())

    async def _org():
        return OrgContext(
            user_id=USER,
            auth_subject="s",
            organization_id=state.org,
            membership_role=state.role,
        )

    async def _project():
        return ProjectContext(
            user_id=USER,
            organization_id=state.org,
            membership_role=state.role,
            project_id=PROJECT,
            project_slug="default",
            is_default_project=True,
        )

    app = FastAPI()
    app.include_router(int_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)
    return state


def test_catalog_can_be_filtered_by_category(api):
    response = api.client.get(
        "/api/integrations", params={"category": registry.CATEGORY_CRM}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert all(
        item["catalog"]["category"] == registry.CATEGORY_CRM for item in body["items"]
    )


def test_catalog_marks_unconnected_planned_providers_as_planned(api):
    response = api.client.get("/api/integrations")
    by_provider = {
        item["catalog"]["provider"]: item for item in response.json()["items"]
    }
    assert by_provider["salesforce"]["setup_status"] == registry.SETUP_PLANNED
    assert by_provider["salesforce"]["integration"] is None


def test_integration_lookup_is_scoped_to_the_callers_organization(api):
    api.session._scalar = [None]
    response = api.client.get(f"/api/integrations/{uuid.uuid4()}")
    assert response.status_code == 404
    assert str(ORG) in _sql(api.session.statements[0])


def test_connecting_is_refused_for_a_member(api):
    api.role = "member"
    response = api.client.post(
        "/api/integrations/connect", json={"provider": "google_drive"}
    )
    assert response.status_code == 403


def test_disconnect_removes_tokens_and_knowledge_documents_even_if_the_provider_revoke_fails(
    api, monkeypatch
):
    row = _row()
    docs = [
        SimpleNamespace(id=uuid.uuid4(), deleted_at=None),
        SimpleNamespace(id=uuid.uuid4(), deleted_at=None),
    ]
    api.session._scalar = [row]
    api.session._scalars = [docs]

    class _Connector:
        def disconnect(self):
            raise ConnectorError("provider already revoked")

    monkeypatch.setattr(
        int_routes.registry, "get_connector", lambda integration: _Connector()
    )

    response = api.client.delete(f"/api/integrations/{row.id}")

    assert response.status_code == 200
    assert response.json() == {
        "detail": "Integration disconnected.",
        "documents_removed": 2,
    }
    assert row.status == IntegrationStatus.disconnected
    assert row.access_token is None
    assert row.refresh_token is None
    assert row.external_account is None
    assert row.last_error is None
    assert all(doc.deleted_at is not None for doc in docs)
    assert len(api.session.executed) == 2  # one chunk purge per synced document
    assert api.session.commits == 1


def test_disconnecting_another_organizations_integration_is_refused_and_touches_nothing(
    api, monkeypatch
):
    foreign = _row(organization_id=OTHER_ORG)
    api.session._scalar = [None]  # org-scoped lookup finds nothing

    called = []
    monkeypatch.setattr(
        int_routes.registry,
        "get_connector",
        lambda integration: called.append(integration),
    )

    response = api.client.delete(f"/api/integrations/{foreign.id}")

    assert response.status_code == 404
    assert called == []
    assert foreign.access_token == "ya29.secret-access"
    assert api.session.commits == 0


def test_disconnecting_needs_an_admin_role(api):
    api.role = "viewer"
    response = api.client.delete(f"/api/integrations/{uuid.uuid4()}")
    assert response.status_code == 403


def test_get_integration_response_never_exposes_stored_tokens(api):
    row = _row()
    api.session._scalar = [row]
    response = api.client.get(f"/api/integrations/{row.id}")
    assert response.status_code == 200
    text = response.text
    assert "ya29.secret-access" not in text
    assert "1//secret-refresh" not in text
