"""Focused regression tests for SSRF, proxy-header and widget isolation guards."""

from starlette.requests import Request

from app.middleware import rate_limit
from app.services import website_crawler, widget_service


def _request(*, peer: str, forwarded: str | None = None) -> Request:
    headers = []
    if forwarded is not None:
        headers.append((b"x-forwarded-for", forwarded.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/widget/event",
            "headers": headers,
            "client": (peer, 1234),
            "server": ("localhost", 8000),
            "scheme": "http",
        }
    )


def test_rendered_crawler_blocks_private_and_non_http_requests(monkeypatch):
    monkeypatch.setattr(
        website_crawler.socket,
        "getaddrinfo",
        lambda *_args: [(0, 0, 0, "", ("93.184.216.34", 0))],
    )

    assert website_crawler.is_safe_render_request("https://public.example/page")
    assert not website_crawler.is_safe_render_request("http://127.0.0.1:8000/admin")
    assert not website_crawler.is_safe_render_request("file:///etc/passwd")
    assert website_crawler.is_safe_render_request("about:blank")


def test_forwarded_ip_is_ignored_from_untrusted_peer(monkeypatch):
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    request = _request(peer="203.0.113.10", forwarded="198.51.100.20")

    assert rate_limit._client_ip(request) == "203.0.113.10"


def test_forwarded_ip_is_used_only_from_configured_proxy(monkeypatch):
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.0/8")
    request = _request(peer="10.20.30.40", forwarded="198.51.100.20, 10.20.30.40")

    assert rate_limit._client_ip(request) == "198.51.100.20"


class _Cache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ttl_seconds=None):
        self.values[key] = value


def test_widget_rate_limit_uses_shared_cache(monkeypatch):
    cache = _Cache()
    monkeypatch.setattr(widget_service, "get_shared_cache", lambda _namespace: cache)
    monkeypatch.setattr(widget_service.time, "time", lambda: 120.0)

    assert not widget_service.rate_limited("widget:visitor", limit=2)
    assert not widget_service.rate_limited("widget:visitor", limit=2)
    assert widget_service.rate_limited("widget:visitor", limit=2)
