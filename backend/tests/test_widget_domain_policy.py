"""Public widget domain allow-list policy and install snippet shape (no network)."""

import asyncio
import re
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.widgets import public
from app.database.models.widget import WidgetStatus
from app.services import widget_service


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("WIDGET_CDN_BASE", raising=False)
    monkeypatch.setenv("FRONTEND_URL", "https://app.example.test")
    monkeypatch.delenv("WIDGET_API_BASE", raising=False)
    monkeypatch.delenv("BACKEND_PUBLIC_URL", raising=False)
    monkeypatch.delenv("PUBLIC_BACKEND_URL", raising=False)
    monkeypatch.delenv("BACKEND_URL", raising=False)


@pytest.mark.parametrize("env", ["production", "prod", "staging", "PRODUCTION"])
def test_production_like_environments_require_an_allow_list(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    assert widget_service.domains_required() is True


@pytest.mark.parametrize("env", ["development", "test", "local"])
def test_local_environments_keep_the_unrestricted_default(monkeypatch, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    assert widget_service.domains_required() is False
    assert widget_service.domain_allowed([], "anything.example") is True


def test_empty_allow_list_fails_closed_when_required():
    assert (
        widget_service.domain_allowed([], "shop.example", require_allow_list=True)
        is False
    )
    assert widget_service.domain_allowed([], "", require_allow_list=True) is False


def test_allow_list_matches_exact_host_and_subdomains_only():
    allowed = ["example.com"]
    assert widget_service.domain_allowed(
        allowed, "example.com", require_allow_list=True
    )
    assert widget_service.domain_allowed(
        allowed, "shop.example.com", require_allow_list=True
    )
    assert not widget_service.domain_allowed(
        allowed, "evil-example.com", require_allow_list=True
    )
    assert not widget_service.domain_allowed(
        allowed, "example.com.evil.test", require_allow_list=True
    )
    assert not widget_service.domain_allowed(allowed, "", require_allow_list=True)


def test_origin_header_is_reduced_to_a_bare_host():
    assert (
        widget_service.origin_host("https://Shop.Example.com:8443/path", None)
        == "shop.example.com"
    )
    assert widget_service.origin_host(None, "https://example.com/page") == "example.com"


def _widget(**overrides):
    base = dict(
        id=uuid.uuid4(),
        public_key="pk_test_123",
        status=WidgetStatus.published,
        organization_id=uuid.uuid4(),
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _guard(monkeypatch, *, domains, origin, env):
    monkeypatch.setenv("ENVIRONMENT", env)
    widget = _widget()

    async def _by_key(_session, _key):
        return widget

    async def _domains(_session, _widget_id):
        return domains

    monkeypatch.setattr(widget_service, "get_widget_by_key", _by_key)
    monkeypatch.setattr(widget_service, "widget_domains", _domains)
    return asyncio.run(
        public._load_live_widget(None, "pk_test_123", origin=origin, referer=None)
    )


def test_public_endpoint_denies_published_widget_with_no_domains_in_production(
    monkeypatch,
):
    with pytest.raises(HTTPException) as exc:
        _guard(
            monkeypatch, domains=[], origin="https://shop.example.com", env="production"
        )
    assert exc.value.status_code == 403


def test_public_endpoint_still_serves_unrestricted_widget_in_development(monkeypatch):
    widget = _guard(
        monkeypatch, domains=[], origin="https://anywhere.test", env="development"
    )
    assert widget.public_key == "pk_test_123"


def test_public_endpoint_enforces_allow_list_in_production(monkeypatch):
    widget = _guard(
        monkeypatch,
        domains=["shop.example.com"],
        origin="https://shop.example.com",
        env="production",
    )
    assert widget.public_key == "pk_test_123"
    with pytest.raises(HTTPException) as exc:
        _guard(
            monkeypatch,
            domains=["shop.example.com"],
            origin="https://attacker.test",
            env="production",
        )
    assert exc.value.status_code == 403


def test_embed_snippet_is_one_script_tag_with_the_widget_key(monkeypatch):
    monkeypatch.setenv("WIDGET_CDN_BASE", "https://cdn.example.test")
    snippet = widget_service.build_embed_snippet("pk_live_abc")
    assert snippet.count("<script") == 1
    assert snippet.count("</script>") == 1
    assert 'src="https://cdn.example.test/widget.js"' in snippet
    assert 'data-widget-id="pk_live_abc"' in snippet
    assert re.fullmatch(
        r'<script src="[^"]+" data-widget-id="[^"]+"( data-api="[^"]+")? async></script>',
        snippet,
    )
