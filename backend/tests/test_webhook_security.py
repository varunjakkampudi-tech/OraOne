"""SSRF and redirect-safety regression tests for customer webhooks."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from app.schemas.webhooks import WebhookCreateRequest, WebhookUpdateRequest
from app.services import webhook_service
from app.services.egress_guard import PinnedTarget


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8000/internal",
        "http://localhost/admin",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.4/secret",
        "http://[::1]/secret",
    ],
)
def test_webhook_create_rejects_private_destinations(url: str):
    with pytest.raises(ValidationError):
        WebhookCreateRequest(url=url)


def test_webhook_update_rejects_private_destination():
    with pytest.raises(ValidationError):
        WebhookUpdateRequest(url="http://127.0.0.1:8080/admin")


def test_webhook_rejects_credentials_and_fragments():
    with pytest.raises(ValidationError):
        WebhookCreateRequest(url="https://user:password@example.com/hook")
    with pytest.raises(ValidationError):
        WebhookUpdateRequest(url="https://example.com/hook#fragment")


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [302, 500])
async def test_delivery_does_not_follow_redirects_and_marks_http_failure(
    monkeypatch, status_code: int
):
    options: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            options.update(kwargs)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return SimpleNamespace(status_code=status_code)

    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        webhook_service,
        "resolve_public_target",
        lambda url, **_: PinnedTarget(url=url),
    )
    endpoint = SimpleNamespace(
        url="https://public.example/hook",
        secret="secret",
    )

    success, response_status, error = await webhook_service._deliver_once(
        endpoint, b"{}", "test.event", delivery_id="evt-1"
    )

    assert success is False
    assert response_status == status_code
    assert error == f"HTTP {status_code}"
    assert options["follow_redirects"] is False


@pytest.mark.asyncio
async def test_delivery_records_connection_failure(monkeypatch):
    class FakeClient:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(
        webhook_service,
        "resolve_public_target",
        lambda url, **_: PinnedTarget(url=url),
    )
    endpoint = SimpleNamespace(url="https://public.example/hook", secret="secret")

    success, response_status, error = await webhook_service._deliver_once(
        endpoint, b"{}", "test.event", delivery_id="evt-2"
    )

    assert success is False
    assert response_status is None
    assert "connection refused" in error
