"""Integration connection scenarios: OAuth authorize and code exchange, refusal when a provider
is not configured or the code is missing, token endpoint outages, and per-tenant connection
lookups.

Every OAuth provider call is replaced. Client credentials are fake values set in the
environment for the test only.
"""

from __future__ import annotations

import uuid
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.api.integrations import routes as integrations_routes
from app.services import oauth_service
from scenario_support import ORG_A, ORG_B, PROJECT_A, FakeSession, org_app, sql

GOOGLE_CLIENT_ID = "scenario-google-client-id"
GOOGLE_CLIENT_SECRET = "scenario-google-client-secret"


@pytest.fixture
def google_configured(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", GOOGLE_CLIENT_ID)
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", GOOGLE_CLIENT_SECRET)
    monkeypatch.delenv("GOOGLE_DRIVE_REDIRECT_URI", raising=False)
    monkeypatch.delenv("GOOGLE_REDIRECT_URI", raising=False)


class _TokenResponse:
    def __init__(self, status_code: int = 200, payload=None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://oauth.example.test/token")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "scenario token failure", request=request, response=response
            )

    def json(self):
        return self._payload


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
def test_authorize_url_carries_client_redirect_scope_and_the_csrf_state(
    google_configured,
):
    url = oauth_service.build_authorize_url("google_drive", state="state-scenario-1")

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )
    assert query["client_id"] == [GOOGLE_CLIENT_ID]
    assert query["state"] == ["state-scenario-1"]
    assert query["response_type"] == ["code"]
    assert query["access_type"] == ["offline"]


@pytest.mark.smoke
def test_authorization_code_is_exchanged_for_tokens_and_the_account_is_named(
    monkeypatch, google_configured
):
    sent: dict = {}

    def token_endpoint(url, data=None, auth=None, timeout=None):
        sent.update(url=url, data=data)
        return _TokenResponse(
            payload={
                "access_token": "scenario-access-token",
                "refresh_token": "scenario-refresh-token",
                "expires_in": 3600,
            }
        )

    def userinfo(url, headers=None, timeout=None):
        assert headers == {"Authorization": "Bearer scenario-access-token"}
        return _TokenResponse(
            status_code=200,
            payload={"user": {"emailAddress": "owner@example.test"}},
        )

    monkeypatch.setattr(oauth_service.httpx, "post", token_endpoint)
    monkeypatch.setattr(oauth_service.httpx, "get", userinfo)

    result = oauth_service.complete_connect("google_drive", code="auth-code-1")

    assert result.access_token == "scenario-access-token"
    assert result.refresh_token == "scenario-refresh-token"
    assert result.external_account == "owner@example.test"
    assert result.token_expires_at is not None
    assert sent["data"]["grant_type"] == "authorization_code"
    assert sent["data"]["code"] == "auth-code-1"


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
def test_connect_is_refused_when_the_provider_has_no_oauth_app(monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    with pytest.raises(oauth_service.OAuthError, match="not configured"):
        oauth_service.build_authorize_url("google_drive", state="s")
    with pytest.raises(oauth_service.OAuthError, match="not configured"):
        oauth_service.complete_connect("google_drive", code="auth-code-1")


@pytest.mark.critical
def test_connect_is_refused_for_an_unknown_provider():
    with pytest.raises(oauth_service.OAuthError, match="not configured"):
        oauth_service.build_authorize_url("made_up_provider", state="s")


@pytest.mark.critical
def test_code_exchange_without_an_authorization_code_is_refused(google_configured):
    with pytest.raises(oauth_service.OAuthError, match="Missing authorization code"):
        oauth_service.complete_connect("google_drive", code=None)


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("http-500", "Token request failed"),
        ("transport-error", "Token request failed"),
        ("no-access-token", "returned no access token"),
    ],
    ids=["provider-500", "provider-unreachable", "empty-token-response"],
)
def test_token_endpoint_failure_is_an_oauth_error_and_no_connection_is_made(
    monkeypatch, google_configured, failure, message
):
    def token_endpoint(url, data=None, auth=None, timeout=None):
        if failure == "transport-error":
            raise httpx.ConnectError("scenario outage")
        if failure == "http-500":
            return _TokenResponse(status_code=500)
        return _TokenResponse(payload={"token_type": "bearer"})

    monkeypatch.setattr(oauth_service.httpx, "post", token_endpoint)

    with pytest.raises(oauth_service.OAuthError, match=message):
        oauth_service.complete_connect("google_drive", code="auth-code-1")


@pytest.mark.regression
def test_account_lookup_outage_still_connects_but_leaves_the_account_unnamed(
    monkeypatch, google_configured
):
    monkeypatch.setattr(
        oauth_service.httpx,
        "post",
        lambda url, data=None, auth=None, timeout=None: _TokenResponse(
            payload={"access_token": "scenario-access-token"}
        ),
    )

    def unavailable(url, headers=None, timeout=None):
        raise httpx.ReadTimeout("scenario timeout")

    monkeypatch.setattr(oauth_service.httpx, "get", unavailable)

    result = oauth_service.complete_connect("google_drive", code="auth-code-1")

    assert result.access_token == "scenario-access-token"
    assert result.external_account is None


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_integration_lookup_by_id_is_scoped_to_the_callers_org():
    session = FakeSession()
    integration_id = uuid.uuid4()

    found = await integrations_routes._integration_for_org(
        session, integration_id=integration_id, organization_id=ORG_A
    )

    assert found is None
    statement = sql(session.statements[0])
    assert str(integration_id) in statement
    assert str(ORG_A) in statement
    assert str(ORG_B) not in statement


@pytest.mark.critical
def test_integration_catalog_reports_only_the_callers_connections(
    google_configured,
):
    session = FakeSession(scalars=[[]])
    client = org_app(
        integrations_routes.router, role="member", session=session, org_id=ORG_A
    )

    response = client.get("/api/integrations")

    assert response.status_code == 200
    statement = sql(session.statements[0])
    assert str(ORG_A) in statement
    assert str(PROJECT_A) in statement
    assert str(ORG_B) not in statement
