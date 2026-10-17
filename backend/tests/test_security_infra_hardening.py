"""Regression tests for health-error redaction and DNS-pinned outbound fetches."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.api import health
from app.services import egress_guard, webhook_service, website_crawler
from app.services.egress_guard import (
    PinnedTarget,
    UnsafeDestinationError,
    resolve_public_target,
)

PUBLIC_IP = "93.184.216.34"
PRIVATE_IP = "10.0.0.5"


def _resolver(*addresses: str, calls: list | None = None):
    """Return a fake ``getaddrinfo`` answering with ``addresses`` in order."""

    def fake(host, port, *args, **kwargs):
        if calls is not None:
            calls.append(host)
        return [(2, 1, 6, "", (address, port or 0)) for address in addresses]

    return fake


def _recording_client(monkeypatch, handler):
    """Make ``httpx.AsyncClient`` use a mock transport and record each request."""
    seen: list[httpx.Request] = []
    real_client = httpx.AsyncClient

    def transport_handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    def factory(**kwargs):
        return real_client(transport=httpx.MockTransport(transport_handler), **kwargs)

    monkeypatch.setattr(webhook_service.httpx, "AsyncClient", factory)
    return seen


# ── health: database error text is not returned to clients ─────────────────


@pytest.mark.asyncio
async def test_db_health_503_body_is_generic(monkeypatch):
    def broken_engine():
        raise RuntimeError(
            "could not connect to postgres://oraone_admin@10.2.3.4/oraone"
        )

    monkeypatch.setattr(health, "init_engine", broken_engine)

    with pytest.raises(HTTPException) as info:
        await health.db_health()

    assert info.value.status_code == 503
    assert info.value.detail == {
        "status": "unhealthy",
        "database": "disconnected",
        "error": "database unavailable",
    }
    rendered = repr(info.value.detail)
    assert "postgres" not in rendered
    assert "10.2.3.4" not in rendered
    assert "RuntimeError" not in rendered


# ── egress guard: resolve once, connect to the validated address ───────────


def test_target_is_pinned_to_validated_address(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(
        egress_guard.socket, "getaddrinfo", _resolver(PUBLIC_IP, calls=calls)
    )

    target = resolve_public_target("https://public.example/hook?x=1")

    assert calls == ["public.example"]
    assert target.url == f"https://{PUBLIC_IP}/hook?x=1"
    assert target.address == PUBLIC_IP
    assert target.host_header == "public.example"
    assert target.sni_hostname == "public.example"


def test_target_keeps_explicit_port_in_url_and_host_header(monkeypatch):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(PUBLIC_IP))

    target = resolve_public_target("http://public.example:8080/a")

    assert target.url == f"http://{PUBLIC_IP}:8080/a"
    assert target.host_header == "public.example:8080"
    assert target.sni_hostname is None


@pytest.mark.parametrize(
    "addresses",
    [(PRIVATE_IP,), (PUBLIC_IP, "127.0.0.1"), ("169.254.169.254",), ("::1",)],
)
def test_target_rejects_any_non_public_address(monkeypatch, addresses):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(*addresses))

    with pytest.raises(UnsafeDestinationError) as info:
        resolve_public_target("https://mixed.example/hook")
    assert info.value.reason == egress_guard.REASON_NON_PUBLIC


def test_unresolvable_host_is_rejected(monkeypatch):
    def fail(*_args, **_kwargs):
        raise OSError("no such host")

    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", fail)

    with pytest.raises(UnsafeDestinationError) as info:
        resolve_public_target("https://missing.example/")
    assert info.value.reason == egress_guard.REASON_UNRESOLVABLE


@pytest.mark.asyncio
async def test_pinned_request_sends_to_ip_with_original_host_and_sni(monkeypatch):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(PUBLIC_IP))

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="ok")

    seen = _recording_client(monkeypatch, handler)
    target = resolve_public_target("https://public.example/hook")

    async with httpx.AsyncClient() as client:
        await egress_guard.pinned_request(client, "POST", target, content=b"{}")

    assert len(seen) == 1
    request = seen[0]
    assert request.url.host == PUBLIC_IP
    assert request.headers["host"] == "public.example"
    assert request.extensions["sni_hostname"] == "public.example"


# ── crawler: DNS rebinding cannot redirect the fetch to private space ──────


@pytest.mark.asyncio
async def test_crawler_fetch_resolves_once_and_connects_to_pinned_ip(monkeypatch):
    calls: list[str] = []
    # A rebinding resolver would answer public first and private second. Only
    # the first answer is ever used because the hostname is resolved once.
    answers = iter([[PUBLIC_IP], [PRIVATE_IP]])

    def rebinding(host, port, *args, **kwargs):
        calls.append(host)
        ip = next(answers)[0]
        return [(2, 1, 6, "", (ip, port or 0))]

    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", rebinding)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, headers={"content-type": "text/html"}, text="<p>hi</p>"
        )

    seen = _recording_client(monkeypatch, handler)

    async with httpx.AsyncClient() as client:
        status, _ctype, text = await website_crawler._fetch(
            client, "https://public.example/page"
        )

    assert status == 200
    assert "hi" in text
    assert calls == ["public.example"]
    assert [r.url.host for r in seen] == [PUBLIC_IP]


@pytest.mark.asyncio
async def test_crawler_fetch_refuses_private_host_before_any_request(monkeypatch):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(PRIVATE_IP))
    seen = _recording_client(monkeypatch, lambda request: httpx.Response(200, text="x"))

    async with httpx.AsyncClient() as client:
        with pytest.raises(website_crawler.URLValidationError):
            await website_crawler._fetch(client, "https://internal.example/")

    assert seen == []


@pytest.mark.asyncio
async def test_crawler_redirect_to_metadata_address_is_blocked(monkeypatch):
    def resolver(host, port, *args, **kwargs):
        ip = "169.254.169.254" if host == "metadata.example" else PUBLIC_IP
        return [(2, 1, 6, "", (ip, port or 0))]

    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", resolver)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            302, headers={"location": "https://metadata.example/latest"}
        )

    seen = _recording_client(monkeypatch, handler)

    async with httpx.AsyncClient() as client:
        with pytest.raises(website_crawler.URLValidationError):
            await website_crawler._fetch(client, "https://public.example/start")

    assert [r.url.host for r in seen] == [PUBLIC_IP]


# ── webhook delivery: validated address is used at send time ───────────────


@pytest.mark.asyncio
async def test_webhook_delivery_connects_to_pinned_ip(monkeypatch):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(PUBLIC_IP))
    seen = _recording_client(monkeypatch, lambda request: httpx.Response(204))
    endpoint = SimpleNamespace(url="https://hooks.public.example/in", secret="s")

    ok, status, error = await webhook_service._deliver_once(
        endpoint, b"{}", "test.event", delivery_id="d1"
    )

    assert (ok, status, error) == (True, 204, None)
    assert seen[0].url.host == PUBLIC_IP
    assert seen[0].headers["host"] == "hooks.public.example"


@pytest.mark.asyncio
async def test_webhook_delivery_rejects_host_that_now_resolves_private(monkeypatch):
    monkeypatch.setattr(egress_guard.socket, "getaddrinfo", _resolver(PRIVATE_IP))
    seen = _recording_client(monkeypatch, lambda request: httpx.Response(204))
    endpoint = SimpleNamespace(url="https://hooks.public.example/in", secret="s")

    ok, status, error = await webhook_service._deliver_once(
        endpoint, b"{}", "test.event", delivery_id="d2"
    )

    assert ok is False
    assert status is None
    assert "non_public" in error
    assert seen == []


def test_pinned_target_headers_are_empty_without_pin():
    target = PinnedTarget(url="http://localhost:8080/x")
    assert target.headers() == {}
    assert target.extensions() == {}
