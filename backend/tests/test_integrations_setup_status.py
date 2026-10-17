"""Integrations catalog status and fail-closed connect behaviour.

No network access: OAuth credentials are absent or fake, and the token
exchange is never reached because every guarded path returns earlier.
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Response

from app.api.integrations import routes
from app.connectors import registry
from app.connectors.base import ConnectorError
from app.services import cache, oauth_service


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-integrations-secret-32-bytes!!!")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://frontend.test")
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
    cache._namespaced_singletons.clear()


def _callback_request(nonce=None):
    """A stand-in for the browser's request: only ``cookies`` is read by the callback."""
    return SimpleNamespace(
        cookies={} if nonce is None else {routes._NONCE_COOKIE: nonce}
    )


def _spec(provider):
    spec = registry.get_spec(provider)
    assert spec is not None
    return spec


def test_planned_provider_reports_planned_even_when_credentials_exist():
    spec = _spec("salesforce")
    assert spec.available is False
    assert (
        registry.provider_setup_status(spec, connected=False, oauth_configured=True)
        == registry.SETUP_PLANNED
    )


def test_available_oauth_provider_without_credentials_requires_setup():
    spec = _spec("google_drive")
    assert (
        registry.provider_setup_status(spec, connected=False, oauth_configured=False)
        == registry.SETUP_REQUIRES_ACCOUNT_SETUP
    )


def test_available_provider_with_credentials_is_not_connected_until_a_row_exists():
    spec = _spec("google_drive")
    assert (
        registry.provider_setup_status(spec, connected=False, oauth_configured=True)
        == registry.SETUP_NOT_CONNECTED
    )
    assert (
        registry.provider_setup_status(spec, connected=True, oauth_configured=True)
        == registry.SETUP_CONNECTED
    )


def test_no_catalog_provider_is_reported_connected_without_a_live_row():
    for spec in registry.list_specs():
        status = registry.provider_setup_status(
            spec, connected=False, oauth_configured=True
        )
        assert status != registry.SETUP_CONNECTED


def test_connect_planned_provider_is_refused_in_plain_language():
    payload = SimpleNamespace(provider="salesforce", code=None, config=None, mock=False)
    pctx = SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )
    from app.api.integrations.routes import connect_integration

    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(connect_integration(payload, Response(), pctx=pctx, session=None))
    assert exc.value.status_code == 409
    assert "planned" in exc.value.detail.lower()


def test_connect_without_oauth_credentials_says_not_configured_and_never_connects(
    monkeypatch,
):
    payload = SimpleNamespace(
        provider="google_drive", code=None, config=None, mock=False
    )
    pctx = SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )
    from app.api.integrations.routes import connect_integration

    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(connect_integration(payload, Response(), pctx=pctx, session=None))
    assert exc.value.status_code == 503
    assert "not configured yet" in exc.value.detail.lower()
    assert "nothing has been connected" in exc.value.detail.lower()


def test_mock_connection_is_never_accepted_on_the_real_connect_path():
    payload = SimpleNamespace(
        provider="google_drive", code=None, config=None, mock=True
    )
    pctx = SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )
    from app.api.integrations.routes import connect_integration

    import asyncio

    with pytest.raises(HTTPException) as exc:
        asyncio.run(connect_integration(payload, Response(), pctx=pctx, session=None))
    assert exc.value.status_code == 503


def test_oauth_callback_redirects_to_studio_not_configured_without_exchanging_code(
    monkeypatch,
):
    import asyncio

    state = routes.issue_oauth_state(
        provider="google_drive",
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        nonce_hash=routes._nonce_hash("browser-nonce"),
    )

    def _no_exchange(*_args, **_kwargs):
        raise AssertionError("token exchange must not run without credentials")

    monkeypatch.setattr(oauth_service, "complete_connect", _no_exchange)
    response = asyncio.run(
        routes.google_oauth_callback(
            request=_callback_request("browser-nonce"),
            code="auth-code",
            state=state,
            error=None,
            session=None,
        )
    )
    assert response.status_code == 302
    assert response.headers["location"] == (
        "http://frontend.test/studio/integrations?error=not_configured"
    )


def test_oauth_callback_does_not_reflect_provider_error_text():
    import asyncio

    response = asyncio.run(
        routes.google_oauth_callback(
            request=_callback_request(),
            code=None,
            state=None,
            error="<script>alert(1)</script>",
            session=None,
        )
    )
    assert response.headers["location"] == (
        "http://frontend.test/studio/integrations?error=provider_denied"
    )


def test_oauth_callback_rejects_tampered_state():
    import asyncio

    response = asyncio.run(
        routes.google_oauth_callback(
            request=_callback_request(),
            code="auth-code",
            state="not-a-real-token",
            error=None,
            session=None,
        )
    )
    assert response.headers["location"].endswith("?error=invalid_state")


def test_exchange_failure_is_a_connector_error_not_a_crash(monkeypatch):
    """A failing token exchange maps to a ConnectorError the API turns into 502."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "fake-client-secret")

    def _boom(*_args, **_kwargs):
        raise oauth_service.OAuthError("Token exchange failed: simulated")

    monkeypatch.setattr(oauth_service.httpx, "post", _boom)
    with pytest.raises(ConnectorError):
        oauth_service.complete_connect("google_drive", code="x")
