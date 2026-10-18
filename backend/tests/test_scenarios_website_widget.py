"""Website chat widget scenarios: domain allow-list, published state, visitor session tokens,
fail-closed database reads, and per-widget isolation.

The widget is loaded through the real resolution helpers with a scripted session. Origin and
Referer are browser-set hints, so the tests pass them explicitly. Environment is pinned.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.widgets import public as widget_public
from app.database.models.widget import WidgetStatus
from scenario_support import ORG_A, ORG_B, FakeSession, sql


class _WidgetSession(FakeSession):
    """Returns ``widget`` for the key lookup and ``domains`` for the allow-list read."""

    def __init__(self, widget=None, domains=(), *, fail_reads: bool = False):
        super().__init__(scalars=[list(domains)], scalar_value=widget)
        self._fail_reads = fail_reads

    async def scalar(self, stmt):
        if self._fail_reads:
            self.statements.append(stmt)
            raise RuntimeError("scenario database outage")
        return await super().scalar(stmt)

    async def scalars(self, stmt):
        if self._fail_reads:
            self.statements.append(stmt)
            raise RuntimeError("scenario database outage")
        return await super().scalars(stmt)


def _widget(org_id: uuid.UUID, key: str, status: str = WidgetStatus.published):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=org_id,
        public_key=key,
        status=status,
        settings={},
        deleted_at=None,
    )


@pytest.fixture(autouse=True)
def development_environment(monkeypatch):
    # Empty allow-lists are permitted outside production-like environments by default.
    monkeypatch.setenv("ENVIRONMENT", "development")


ACME_ORIGIN = "https://www.acme.example"
ACME_ORIGIN_SUBDOMAIN = "https://chat.acme.example"


# ───────────────────────── happy path ─────────────────────────


@pytest.mark.smoke
async def test_published_widget_loads_for_an_allowed_site_and_subdomain():
    widget = _widget(ORG_A, "pk_scenario_a")
    session = _WidgetSession(widget=widget, domains=["acme.example"])

    loaded = await widget_public._load_live_widget(
        session, "pk_scenario_a", origin=ACME_ORIGIN, referer=None
    )
    assert loaded is widget

    loaded_sub = await widget_public._load_live_widget(
        session, "pk_scenario_a", origin=ACME_ORIGIN_SUBDOMAIN, referer=None
    )
    assert loaded_sub is widget


# ───────────────────────── refusals ─────────────────────────


@pytest.mark.critical
async def test_draft_or_paused_widget_is_not_served():
    for status in (WidgetStatus.draft, WidgetStatus.paused):
        session = _WidgetSession(
            widget=_widget(ORG_A, "pk_scenario_a", status=status),
            domains=["acme.example"],
        )
        with pytest.raises(HTTPException) as refused:
            await widget_public._load_live_widget(
                session, "pk_scenario_a", origin=ACME_ORIGIN, referer=None
            )
        assert refused.value.status_code == 403
        assert refused.value.detail == "Widget is not live."


@pytest.mark.critical
@pytest.mark.parametrize(
    ("origin", "referer"),
    [
        ("https://evil.example", None),
        (None, None),
        ("https://acme.example.evil.test", None),
    ],
    ids=["other-site", "no-origin-or-referer", "lookalike-suffix"],
)
async def test_widget_refuses_sites_outside_its_allow_list(origin, referer):
    session = _WidgetSession(
        widget=_widget(ORG_A, "pk_scenario_a"), domains=["acme.example"]
    )

    with pytest.raises(HTTPException) as refused:
        await widget_public._load_live_widget(
            session, "pk_scenario_a", origin=origin, referer=referer
        )

    assert refused.value.status_code == 403
    assert "not authorized for this domain" in refused.value.detail


@pytest.mark.critical
async def test_production_widget_with_no_allow_list_denies_every_site(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    session = _WidgetSession(widget=_widget(ORG_A, "pk_scenario_a"), domains=[])

    with pytest.raises(HTTPException) as refused:
        await widget_public._load_live_widget(
            session, "pk_scenario_a", origin=ACME_ORIGIN, referer=None
        )

    assert refused.value.status_code == 403


@pytest.mark.critical
async def test_visitor_session_token_from_another_visitor_is_refused():
    widget = _widget(ORG_A, "pk_scenario_a")
    stored = SimpleNamespace(
        session_token_hash=widget_public._hash_session_token("token-visitor-one")
    )
    session = _WidgetSession(widget=stored)

    with pytest.raises(HTTPException) as refused:
        await widget_public._authorized_visitor_session(
            session, widget, "visitor-one", "token-visitor-two"
        )

    assert refused.value.status_code == 403
    assert refused.value.detail == widget_public._SESSION_DENIED


@pytest.mark.critical
async def test_legacy_visitor_without_a_token_digest_fails_closed():
    widget = _widget(ORG_A, "pk_scenario_a")
    legacy = SimpleNamespace(session_token_hash=None)
    session = _WidgetSession(widget=legacy)

    with pytest.raises(HTTPException):
        await widget_public._authorized_visitor_session(
            session, widget, "visitor-legacy", "any-token"
        )


# ───────────────────────── external failure ─────────────────────────


@pytest.mark.regression
async def test_allow_list_read_failure_fails_closed_and_serves_nothing():
    session = _WidgetSession(
        widget=_widget(ORG_A, "pk_scenario_a"),
        domains=["acme.example"],
        fail_reads=True,
    )

    with pytest.raises(RuntimeError, match="scenario database outage"):
        await widget_public._load_live_widget(
            session, "pk_scenario_a", origin=ACME_ORIGIN, referer=None
        )


# ───────────────────────── tenant isolation ─────────────────────────


@pytest.mark.critical
async def test_another_tenants_widget_cannot_be_used_from_this_tenants_site():
    widget_b = _widget(ORG_B, "pk_scenario_b")
    session = _WidgetSession(widget=widget_b, domains=["bravo.example"])

    with pytest.raises(HTTPException) as refused:
        await widget_public._load_live_widget(
            session, "pk_scenario_b", origin=ACME_ORIGIN, referer=None
        )

    assert refused.value.status_code == 403
    assert str(widget_b.id) in sql(session.statements[-1])


@pytest.mark.critical
async def test_allow_list_lookup_is_scoped_to_the_resolved_widget():
    widget_b = _widget(ORG_B, "pk_scenario_b")
    session = _WidgetSession(widget=widget_b, domains=["bravo.example"])

    loaded = await widget_public._load_live_widget(
        session, "pk_scenario_b", origin="https://bravo.example", referer=None
    )

    assert loaded is widget_b
    assert str(widget_b.id) in sql(session.statements[-1])
