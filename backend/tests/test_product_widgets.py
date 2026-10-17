"""Website chat widget: publish guards, public domain allow-list, live-only chat and rate limiting.

Complements test_widget_domain_policy.py and test_security_boundaries.py. No database and no
network: widget rows are in-memory objects and the shared rate-limit cache is replaced.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.widgets import public
from app.api.widgets import routes as widget_routes
from app.database.models.widget import WidgetStatus
from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from app.services import widget_service

ORG = uuid.uuid4()
OTHER_ORG = uuid.uuid4()
USER = uuid.uuid4()
KEY = "pk_live_test_widget"


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    for name in (
        "WIDGET_CDN_BASE",
        "WIDGET_API_BASE",
        "BACKEND_PUBLIC_URL",
        "PUBLIC_BACKEND_URL",
        "BACKEND_URL",
    ):
        monkeypatch.delenv(name, raising=False)


def _widget(**overrides):
    base = dict(
        id=uuid.uuid4(),
        organization_id=ORG,
        public_key=KEY,
        status=WidgetStatus.published,
        settings={},
        published_at=None,
        deleted_at=None,
        agent_id=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _patch_lookup(monkeypatch, widget, domains):
    async def by_key(session, key):
        return widget if widget is not None and key == KEY else None

    async def domains_for(session, widget_id):
        return domains

    monkeypatch.setattr(widget_service, "get_widget_by_key", by_key)
    monkeypatch.setattr(widget_service, "widget_domains", domains_for)


def _live(origin, *, domains, env, monkeypatch, widget=None):
    monkeypatch.setenv("ENVIRONMENT", env)
    widget = widget or _widget()
    _patch_lookup(monkeypatch, widget, domains)
    return asyncio.run(public._load_live_widget(None, KEY, origin=origin, referer=None))


# ── chat endpoints: live widgets only ────────────────────────────────────────


def test_unknown_widget_key_is_not_found(monkeypatch):
    _patch_lookup(monkeypatch, None, [])
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            public._load_live_widget(None, "pk_missing", origin=None, referer=None)
        )
    assert exc.value.status_code == 404


def test_draft_or_paused_widget_does_not_answer_visitors(monkeypatch):
    for status in (WidgetStatus.draft, WidgetStatus.paused):
        with pytest.raises(HTTPException) as exc:
            _live(
                "https://shop.example.com",
                domains=[],
                env="development",
                monkeypatch=monkeypatch,
                widget=_widget(status=status),
            )
        assert exc.value.status_code == 403
        assert exc.value.detail == "Widget is not live."


def test_visitor_from_an_allowed_subdomain_is_served_in_production(monkeypatch):
    widget = _live(
        "https://www.shop.example.com",
        domains=["shop.example.com"],
        env="production",
        monkeypatch=monkeypatch,
    )
    assert widget.public_key == KEY


@pytest.mark.parametrize(
    "origin",
    [
        "https://shop.example.com.attacker.test",  # allowed name used as a prefix
        "https://evilshop.example.com",  # suffix match without a dot boundary
        "https://attacker.test",
    ],
)
def test_lookalike_or_foreign_origins_are_refused_in_production(monkeypatch, origin):
    with pytest.raises(HTTPException) as exc:
        _live(
            origin,
            domains=["shop.example.com"],
            env="production",
            monkeypatch=monkeypatch,
        )
    assert exc.value.status_code == 403
    assert "not authorized for this domain" in exc.value.detail


def test_referer_is_used_when_origin_header_is_missing(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    _patch_lookup(monkeypatch, _widget(), ["shop.example.com"])
    widget = asyncio.run(
        public._load_live_widget(
            None, KEY, origin=None, referer="https://shop.example.com/cart"
        )
    )
    assert widget.public_key == KEY


def test_production_widget_with_no_allowed_domains_serves_nobody(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        _live(
            "https://shop.example.com",
            domains=[],
            env="staging",
            monkeypatch=monkeypatch,
        )
    assert exc.value.status_code == 403


def test_visitor_over_the_message_limit_is_asked_to_slow_down(monkeypatch):
    widget = _widget(settings={"rate_limit_per_min": 3})
    seen = {}

    def over_limit(key, *, limit, window_seconds):
        seen.update(key=key, limit=limit, window=window_seconds)
        return True

    monkeypatch.setattr(widget_service, "rate_limited", over_limit)
    with pytest.raises(HTTPException) as exc:
        public._check_rate(widget, "visitor-1")
    assert exc.value.status_code == 429
    assert seen == {"key": f"{KEY}:visitor-1", "limit": 3, "window": 60}


def test_visitor_within_the_message_limit_is_not_blocked(monkeypatch):
    monkeypatch.setattr(widget_service, "rate_limited", lambda *a, **k: False)
    public._check_rate(_widget(), "visitor-1")  # does not raise


# ── public configuration ─────────────────────────────────────────────────────


def _config_call(monkeypatch, widget, origin, env, domains):
    monkeypatch.setenv("ENVIRONMENT", env)
    _patch_lookup(monkeypatch, widget, domains)
    monkeypatch.setattr(
        public, "WidgetPublicConfig", lambda **kw: SimpleNamespace(**kw)
    )
    monkeypatch.setattr(
        widget_service, "public_config_dict", lambda w, d: {"public_key": w.public_key}
    )
    return asyncio.run(
        public.widget_config(KEY, origin=origin, referer=None, session=None)
    )


def test_published_widget_config_is_refused_to_an_unlisted_site_in_production(
    monkeypatch,
):
    with pytest.raises(HTTPException) as exc:
        _config_call(
            monkeypatch,
            _widget(),
            "https://attacker.test",
            "production",
            ["shop.example.com"],
        )
    assert exc.value.status_code == 403


def test_draft_widget_config_is_readable_for_the_dashboard_preview(monkeypatch):
    config = _config_call(
        monkeypatch,
        _widget(status=WidgetStatus.draft),
        "https://attacker.test",
        "production",
        ["shop.example.com"],
    )
    assert config.public_key == KEY


# ── dashboard routes ─────────────────────────────────────────────────────────


@pytest.fixture
def dashboard(monkeypatch):
    monkeypatch.setattr(widget_routes, "audit", lambda *a, **k: None)
    monkeypatch.setattr(widget_routes, "_read", lambda session, widget: _async(widget))
    state = SimpleNamespace(
        role="owner",
        org=ORG,
        widget=None,
        session=SimpleNamespace(commit=_async, refresh=_async),
    )

    async def _org():
        return OrgContext(
            user_id=USER,
            auth_subject="s",
            organization_id=state.org,
            membership_role=state.role,
        )

    app = FastAPI()
    app.include_router(widget_routes.router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_db] = lambda: state.session
    state.client = TestClient(app)
    return state


async def _async(*args, **kwargs):
    return args[-1] if args else None


def test_member_cannot_publish_a_widget(dashboard):
    dashboard.role = "member"
    response = dashboard.client.post(f"/api/widgets/{uuid.uuid4()}/publish")
    assert response.status_code == 403


def test_publishing_another_organizations_widget_is_not_found(dashboard, monkeypatch):
    seen = {}

    async def not_mine(session, *, widget_id, organization_id):
        seen["org"] = organization_id
        return None

    monkeypatch.setattr(widget_routes, "_widget_for_org", not_mine)
    ctx = OrgContext(
        user_id=USER, auth_subject="s", organization_id=ORG, membership_role="owner"
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            widget_routes.publish_widget(
                uuid.uuid4(), publish=True, ctx=ctx, session=dashboard.session
            )
        )
    assert exc.value.status_code == 404
    assert seen["org"] == ORG


def test_deleting_another_organizations_widget_is_not_found(dashboard, monkeypatch):
    async def not_mine(session, *, widget_id, organization_id):
        return None

    monkeypatch.setattr(widget_routes, "_widget_for_org", not_mine)
    ctx = OrgContext(
        user_id=USER,
        auth_subject="s",
        organization_id=OTHER_ORG,
        membership_role="owner",
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            widget_routes.delete_widget(
                uuid.uuid4(), ctx=ctx, session=dashboard.session
            )
        )
    assert exc.value.status_code == 404


def test_publish_sets_the_widget_live_and_unpublish_pauses_it(dashboard, monkeypatch):
    widget = _widget(status=WidgetStatus.paused)

    async def mine(session, *, widget_id, organization_id):
        return widget

    monkeypatch.setattr(widget_routes, "_widget_for_org", mine)
    ctx = OrgContext(
        user_id=USER, auth_subject="s", organization_id=ORG, membership_role="owner"
    )

    asyncio.run(
        widget_routes.publish_widget(
            widget.id, publish=True, ctx=ctx, session=dashboard.session
        )
    )
    assert widget.status == WidgetStatus.published
    assert widget.published_at is not None

    asyncio.run(
        widget_routes.publish_widget(
            widget.id, publish=False, ctx=ctx, session=dashboard.session
        )
    )
    assert widget.status == WidgetStatus.paused


def test_delete_hides_the_widget_and_stops_it_serving(dashboard, monkeypatch):
    widget = _widget()

    async def mine(session, *, widget_id, organization_id):
        return widget

    monkeypatch.setattr(widget_routes, "_widget_for_org", mine)
    ctx = OrgContext(
        user_id=USER, auth_subject="s", organization_id=ORG, membership_role="owner"
    )

    result = asyncio.run(
        widget_routes.delete_widget(widget.id, ctx=ctx, session=dashboard.session)
    )

    assert result == {"detail": "Widget deleted."}
    assert widget.deleted_at is not None
    assert widget.status == WidgetStatus.paused
