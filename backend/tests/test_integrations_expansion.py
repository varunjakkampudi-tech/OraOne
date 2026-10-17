"""Integrations expansion: new provider status, fail-closed OAuth, signed outbound events.

No network access. OAuth authorize URLs are built locally, token exchanges are never
reached, and signed-event delivery runs against an in-memory httpx transport. Public
IP literals are used for the allowed destination, so no DNS lookup happens.
"""

import asyncio
import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi import HTTPException, Response

from app.api.integrations import routes
from app.connectors import registry
from app.database.models.integration import IntegrationStatus
from app.services import cache, oauth_service, signed_webhook

OAUTH_PROVIDERS = ["google_calendar", "google_sheets", "slack", "hubspot", "notion"]
PLANNED_PROVIDERS = ["zapier", "make", "generic_webhook", "salesforce"]

_ALL_OAUTH_ENV = [
    f"{prefix}_{suffix}"
    for prefix in (
        "GOOGLE",
        "GOOGLE_CALENDAR",
        "GOOGLE_SHEETS",
        "SLACK",
        "HUBSPOT",
        "NOTION",
    )
    for suffix in ("CLIENT_ID", "CLIENT_SECRET")
]
FAKE_CLIENT_ID = "fake-client-id-for-tests"
FAKE_CLIENT_SECRET = "fake-client-secret-for-tests"


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "test-integrations-secret-32-bytes!!!")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("FRONTEND_URL", "http://frontend.test")
    for name in _ALL_OAUTH_ENV:
        monkeypatch.delenv(name, raising=False)
    cache._namespaced_singletons.clear()


def _configure(monkeypatch, provider: str) -> None:
    prefix = oauth_service._OAUTH_PROVIDERS[provider]["env_prefix"]
    monkeypatch.setenv(f"{prefix}_CLIENT_ID", FAKE_CLIENT_ID)
    monkeypatch.setenv(f"{prefix}_CLIENT_SECRET", FAKE_CLIENT_SECRET)


def _pctx():
    return SimpleNamespace(
        org=SimpleNamespace(organization_id=uuid.uuid4(), user_id=uuid.uuid4()),
        project_id=uuid.uuid4(),
    )


def _connect(provider: str, *, mock: bool = False):
    payload = SimpleNamespace(provider=provider, code=None, config=None, mock=mock)
    return asyncio.run(
        routes.connect_integration(payload, Response(), pctx=_pctx(), session=None)
    )


# ── catalog status ──────────────────────────────────────────────────────────


@pytest.mark.parametrize("provider", OAUTH_PROVIDERS)
def test_oauth_provider_needs_setup_without_credentials(provider):
    spec = registry.get_spec(provider)
    assert spec is not None and spec.available is True
    status = registry.provider_setup_status(
        spec, connected=False, oauth_configured=oauth_service.is_configured(provider)
    )
    assert status == registry.SETUP_REQUIRES_ACCOUNT_SETUP


@pytest.mark.parametrize("provider", OAUTH_PROVIDERS)
def test_oauth_provider_is_not_connected_once_credentials_exist(provider, monkeypatch):
    _configure(monkeypatch, provider)
    spec = registry.get_spec(provider)
    status = registry.provider_setup_status(
        spec, connected=False, oauth_configured=oauth_service.is_configured(provider)
    )
    assert status == registry.SETUP_NOT_CONNECTED


@pytest.mark.parametrize("provider", PLANNED_PROVIDERS)
def test_planned_provider_stays_planned_even_with_credentials(provider, monkeypatch):
    for name in ("GOOGLE_CALENDAR", "SLACK", "HUBSPOT", "NOTION"):
        monkeypatch.setenv(f"{name}_CLIENT_ID", FAKE_CLIENT_ID)
        monkeypatch.setenv(f"{name}_CLIENT_SECRET", FAKE_CLIENT_SECRET)
    spec = registry.get_spec(provider)
    assert spec is not None and spec.available is False
    assert (
        registry.provider_setup_status(spec, connected=False, oauth_configured=True)
        == registry.SETUP_PLANNED
    )


def test_sync_is_planned_for_every_new_provider():
    for provider in OAUTH_PROVIDERS + ["zapier", "make", "generic_webhook"]:
        spec = registry.get_spec(provider)
        assert spec is not None
        if provider != "google_drive":
            assert spec.sync_available is False, provider


def test_no_provider_is_reported_connected_without_a_live_row(monkeypatch):
    for provider in OAUTH_PROVIDERS:
        _configure(monkeypatch, provider)
    for spec in registry.list_specs():
        status = registry.provider_setup_status(
            spec,
            connected=False,
            oauth_configured=oauth_service.is_configured(spec.provider),
        )
        assert status != registry.SETUP_CONNECTED, spec.provider


def test_catalog_item_lists_setting_names_only(monkeypatch):
    _configure(monkeypatch, "google_calendar")
    names = oauth_service.required_settings("google_calendar")
    assert names == ["GOOGLE_CALENDAR_CLIENT_ID", "GOOGLE_CALENDAR_CLIENT_SECRET"]
    item = routes._catalog_item(registry.get_spec("google_calendar"))
    assert item.required_settings == names
    assert FAKE_CLIENT_ID not in str(item.model_dump())
    assert FAKE_CLIENT_SECRET not in str(item.model_dump())


# ── connect: fail closed without credentials ────────────────────────────────


@pytest.mark.parametrize("provider", OAUTH_PROVIDERS)
def test_connect_without_credentials_returns_503_and_connects_nothing(provider):
    with pytest.raises(HTTPException) as exc:
        _connect(provider)
    assert exc.value.status_code == 503
    detail = exc.value.detail.lower()
    assert "not configured yet" in detail
    assert "nothing has been connected" in detail
    prefix = oauth_service._OAUTH_PROVIDERS[provider]["env_prefix"]
    assert f"{prefix}_CLIENT_ID" in exc.value.detail
    assert f"{prefix}_CLIENT_SECRET" in exc.value.detail


@pytest.mark.parametrize("provider", OAUTH_PROVIDERS)
def test_mock_connection_is_still_refused_for_new_providers(provider):
    with pytest.raises(HTTPException) as exc:
        _connect(provider, mock=True)
    assert exc.value.status_code == 503


@pytest.mark.parametrize("provider", PLANNED_PROVIDERS)
def test_planned_providers_cannot_be_connected(provider):
    with pytest.raises(HTTPException) as exc:
        _connect(provider)
    assert exc.value.status_code == 409


@pytest.mark.parametrize(
    "provider, expected_scope",
    [
        ("google_calendar", "https://www.googleapis.com/auth/calendar.events"),
        ("google_sheets", "https://www.googleapis.com/auth/spreadsheets"),
        ("slack", "chat:write"),
    ],
)
def test_configured_oauth_provider_returns_authorize_url_only(
    provider, expected_scope, monkeypatch
):
    _configure(monkeypatch, provider)
    result = _connect(provider)
    assert result.integration is None
    assert result.authorize_url is not None
    query = parse_qs(urlsplit(result.authorize_url).query)
    assert query["client_id"] == [FAKE_CLIENT_ID]
    assert query["scope"] == [expected_scope]
    assert query["redirect_uri"] == [
        "http://localhost:3000/api/integrations/oauth/callback"
    ]


def test_notion_authorize_url_asks_for_user_owner_and_no_scope(monkeypatch):
    _configure(monkeypatch, "notion")
    query = parse_qs(urlsplit(_connect("notion").authorize_url).query)
    assert query["owner"] == ["user"]
    assert "scope" not in query


def test_generic_callback_path_is_registered_alongside_google():
    paths = {getattr(route, "path", None) for route in routes.router.routes}
    assert "/api/integrations/oauth/callback" in paths
    assert "/api/integrations/google/callback" in paths


# ── no fake connection: sync stays planned ───────────────────────────────────


class _OneRowSession:
    def __init__(self, row):
        self._row = row

    async def scalar(self, *_args, **_kwargs):
        return self._row

    def add(self, _obj):
        raise AssertionError("no sync job may be created for a planned sync")


@pytest.mark.parametrize("provider", OAUTH_PROVIDERS)
def test_sync_on_a_live_planned_provider_is_refused(provider):
    row = SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        provider=provider,
        status=IntegrationStatus.connected,
    )
    ctx = SimpleNamespace(organization_id=row.organization_id, user_id=uuid.uuid4())
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            routes.trigger_sync(
                row.id,
                background_tasks=SimpleNamespace(add_task=lambda *a, **k: None),
                ctx=ctx,
                session=_OneRowSession(row),
            )
        )
    assert exc.value.status_code == 409
    assert "planned" in exc.value.detail.lower()


# ── signed outbound events ───────────────────────────────────────────────────

SECRET = "whsec_test_signing_secret_0123456789"
PUBLIC_URL = "https://93.184.216.34/hooks/oraone"
NOW = 1_800_000_000


def _capture(status: int = 204, *, raise_exc: Exception | None = None):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if raise_exc is not None:
            raise raise_exc
        return httpx.Response(status)

    return calls, httpx.MockTransport(handler)


def _send(
    url=PUBLIC_URL, *, transport, delivery_id="dlv_test_1", now=NOW, secret=SECRET
):
    return asyncio.run(
        signed_webhook.send_event(
            url,
            event="lead.created",
            data={"lead_id": 42, "name": "Ada"},
            secret=secret,
            delivery_id=delivery_id,
            now=now,
            transport=transport,
        )
    )


def _received(request: httpx.Request) -> dict:
    headers = {k.lower(): v for k, v in request.headers.items()}
    return {
        "body": request.content,
        "delivery": headers["x-oraone-delivery"],
        "timestamp": headers["x-oraone-timestamp"],
        "signature": headers["x-oraone-signature"],
        "event": headers["x-oraone-event"],
    }


def test_signed_event_round_trip_verifies_with_the_same_secret():
    calls, transport = _capture(204)
    outcome = _send(transport=transport)
    assert outcome.delivered is True and outcome.status_code == 204
    assert len(calls) == 1
    got = _received(calls[0])
    assert got["signature"].startswith("sha256=")
    assert got["event"] == "lead.created"
    signed_webhook.verify(
        secret=SECRET,
        body=got["body"],
        delivery_id=got["delivery"],
        timestamp_header=got["timestamp"],
        signature_header=got["signature"],
        now=NOW,
    )


def test_tampered_body_fails_signature_verification():
    calls, transport = _capture(204)
    _send(transport=transport)
    got = _received(calls[0])
    with pytest.raises(signed_webhook.SignatureRejected) as exc:
        signed_webhook.verify(
            secret=SECRET,
            body=got["body"].replace(b"Ada", b"Eve"),
            delivery_id=got["delivery"],
            timestamp_header=got["timestamp"],
            signature_header=got["signature"],
            now=NOW,
        )
    assert exc.value.reason == "bad_signature"


def test_wrong_secret_or_swapped_delivery_id_fails_verification():
    calls, transport = _capture(204)
    _send(transport=transport)
    got = _received(calls[0])
    for kwargs in (
        {"secret": "whsec_a_different_secret_0123456789"},
        {"delivery_id": "dlv_other"},
    ):
        base = {
            "secret": SECRET,
            "body": got["body"],
            "delivery_id": got["delivery"],
            "timestamp_header": got["timestamp"],
            "signature_header": got["signature"],
            "now": NOW,
        }
        base.update(kwargs)
        with pytest.raises(signed_webhook.SignatureRejected):
            signed_webhook.verify(**base)


@pytest.mark.parametrize("skew", [-301, 301, 3600])
def test_replay_outside_the_window_is_refused(skew):
    calls, transport = _capture(204)
    _send(transport=transport)
    got = _received(calls[0])
    with pytest.raises(signed_webhook.SignatureRejected) as exc:
        signed_webhook.verify(
            secret=SECRET,
            body=got["body"],
            delivery_id=got["delivery"],
            timestamp_header=got["timestamp"],
            signature_header=got["signature"],
            now=NOW + skew,
        )
    assert exc.value.reason == "stale_timestamp"


def test_request_at_the_edge_of_the_window_is_accepted():
    calls, transport = _capture(204)
    _send(transport=transport)
    got = _received(calls[0])
    signed_webhook.verify(
        secret=SECRET,
        body=got["body"],
        delivery_id=got["delivery"],
        timestamp_header=got["timestamp"],
        signature_header=got["signature"],
        now=NOW + signed_webhook.REPLAY_WINDOW_SECONDS,
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://93.184.216.34/hooks",  # plain http
        "https://127.0.0.1/hooks",  # loopback
        "https://10.0.0.5/hooks",  # private
        "https://192.168.1.10/hooks",  # private
        "https://169.254.169.254/latest/meta-data",  # link-local / cloud metadata
        "https://[::1]/hooks",  # IPv6 loopback
        "https://localhost/hooks",  # local host name
        "ftp://93.184.216.34/hooks",
    ],
)
def test_unsafe_destinations_are_refused_before_any_request(url):
    calls, transport = _capture(204)
    with pytest.raises(signed_webhook.SignedWebhookError):
        _send(url, transport=transport)
    assert calls == []


def test_short_signing_secret_is_refused_before_any_request():
    calls, transport = _capture(204)
    with pytest.raises(signed_webhook.SignedWebhookError):
        _send(transport=transport, secret="short")
    assert calls == []


def test_failed_delivery_is_recorded_once_with_no_retry():
    calls, transport = _capture(500)
    outcome = _send(transport=transport, delivery_id="dlv_no_retry")
    assert outcome.delivered is False
    assert outcome.status_code == 500
    assert outcome.error == "HTTP 500"
    assert outcome.delivery_id == "dlv_no_retry"
    assert len(calls) == 1
    assert _received(calls[0])["delivery"] == "dlv_no_retry"


def test_transport_error_is_recorded_as_an_outcome_not_a_fake_success():
    calls, transport = _capture(raise_exc=httpx.ConnectError("refused"))
    outcome = _send(transport=transport)
    assert outcome.delivered is False
    assert outcome.status_code is None
    assert outcome.error == "ConnectError"
    assert len(calls) == 1
