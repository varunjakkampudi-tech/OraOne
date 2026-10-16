"""Regression tests for public website ingestion safety."""

import pytest
from fastapi import HTTPException

from app.api.knowledge import sources
from app.services.website_crawler import URLValidationError


def test_guard_public_url_rejects_loopback_and_non_http_urls():
    with pytest.raises(HTTPException) as loopback:
        sources._guard_public_url("http://127.0.0.1:8000/internal")
    assert loopback.value.status_code == 422

    with pytest.raises(HTTPException) as scheme:
        sources._guard_public_url("file:///etc/passwd")
    assert scheme.value.status_code == 422


class _Response:
    def __init__(self, status_code, *, headers=None, body=b""):
        self.status_code = status_code
        self.headers = headers or {}
        self._body = body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("upstream failure")

    async def aiter_bytes(self):
        yield self._body


class _Client:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requested = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def stream(self, method, url, headers):
        self.requested.append((method, url, headers))
        return next(self.responses)


@pytest.mark.asyncio
async def test_fetch_public_page_revalidates_redirect_target(monkeypatch):
    start = "https://public.example/page"
    client = _Client(
        [
            _Response(302, headers={"location": "http://127.0.0.1:8000/admin"}),
        ]
    )

    def validate(value):
        if value == start:
            return value
        raise URLValidationError("private destination")

    monkeypatch.setattr(sources, "validate_url", validate)
    monkeypatch.setattr(sources.httpx, "AsyncClient", lambda **_kwargs: client)

    with pytest.raises(HTTPException) as exc:
        await sources._fetch_public_page(start)

    assert exc.value.status_code == 422
    assert len(client.requested) == 1


@pytest.mark.asyncio
async def test_fetch_public_page_enforces_response_size_cap(monkeypatch):
    start = "https://public.example/large"
    client = _Client(
        [
            _Response(
                200,
                headers={"content-length": str(sources._MAX_FETCH_BYTES + 1)},
                body=b"x",
            ),
        ]
    )
    monkeypatch.setattr(sources, "validate_url", lambda value: value)
    monkeypatch.setattr(sources.httpx, "AsyncClient", lambda **_kwargs: client)

    with pytest.raises(HTTPException) as exc:
        await sources._fetch_public_page(start)

    assert exc.value.status_code == 413
