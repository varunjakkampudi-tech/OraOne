"""Admin log viewer: access control, redaction, export cap, error capture, audit.

No test touches a real database. Route handlers read through ``error_events``
functions that are replaced with in-memory rows, and persisted error rows are
captured by a fake session factory.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects import postgresql

from app.api.admin_logs import routes as admin_logs_routes
from app.core.log_redaction import format_frames, replace_raw_path, scrub_text
from app.database import session as db_session
from app.database.models.error_event import ErrorEvent
from app.database.models.user import UserRole
from app.database.session import get_db
from app.middleware import request_context
from app.middleware.platform_context import (
    PlatformContext,
    get_current_platform_context,
)
from app.middleware.request_context import install_request_context, safe_request_id
from app.services import error_events, ops_service

SECRET_TOKEN = "tok-SECRET-9f8e7d6c5b4a3210fedcba"
EMAIL = "alice@example.com"


def _event(
    *,
    request_id: str = "req-0001-abcdef",
    route: str = "/api/admin/logs/errors",
    status_code: int = 500,
    message: str | None = None,
    stack: str | None = None,
    occurred_at: datetime | None = None,
) -> ErrorEvent:
    return ErrorEvent(
        id=uuid.uuid4(),
        request_id=request_id,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        method="GET",
        route=route,
        status_code=status_code,
        duration_ms=12,
        exception_type="RuntimeError",
        message=message,
        stack_trace=stack,
        release_version="test",
        trace_id=None,
        actor_hash="sha256:0123456789abcdef",
        org_hash="sha256:fedcba9876543210",
    )


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _ExportSession:
    """Returns every row it is given and remembers the statements it was asked to run."""

    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def scalars(self, stmt):
        self.statements.append(stmt)
        return _Result(self.rows)


class _CaptureSession:
    def __init__(self, sink):
        self.sink = sink

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def add(self, obj):
        self.sink.append(obj)

    async def commit(self):
        return None

    async def rollback(self):
        return None


@pytest.fixture
def persisted(monkeypatch):
    """Rows the request middleware tries to write to ``error_events``."""
    sink: list = []
    monkeypatch.setattr(db_session, "AsyncSessionLocal", lambda: _CaptureSession(sink))
    return sink


@pytest.fixture
def audit_calls(monkeypatch):
    calls: list[tuple[str, dict]] = []

    def _capture(action, **kwargs):
        calls.append((action, kwargs))

    async def _noop_flush(session):
        return 0

    monkeypatch.setattr(admin_logs_routes, "audit", _capture)
    monkeypatch.setattr(admin_logs_routes, "flush_pending", _noop_flush)
    return calls


def _context(role: UserRole) -> PlatformContext:
    user = SimpleNamespace(
        id="00000000-0000-4000-8000-0000000000aa", email="ops@example.com"
    )
    return PlatformContext(user=user, auth_subject="sub-ops", role=role)


@pytest.fixture
def server_app():
    from server import app

    yield app
    app.dependency_overrides.clear()


def _client(app, role: UserRole | None) -> AsyncClient:
    async def _db():
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = _db
    if role is not None:

        async def _ctx() -> PlatformContext:
            return _context(role)

        app.dependency_overrides[get_current_platform_context] = _ctx
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def rows_in_store(monkeypatch):
    rows = [
        _event(request_id="req-0001-abcdef", message=f"lookup failed for {EMAIL}"),
        _event(
            request_id="req-0002-abcdef",
            route="/api/omnichannel/telegram/{bot_token}/inbound",
            message=f"bad token {SECRET_TOKEN}",
            stack="Traceback ...",
        ),
    ]

    async def _list(session, **kwargs):
        return rows, len(rows)

    async def _get(session, request_id):
        return next((r for r in rows if r.request_id == request_id), None)

    monkeypatch.setattr(error_events, "list_error_events", _list)
    monkeypatch.setattr(error_events, "get_error_event", _get)
    return rows


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.super_admin, 200),
        (UserRole.admin, 200),
        (UserRole.manager, 403),
        (UserRole.user, 403),
    ],
)
async def test_only_platform_admins_can_read_error_list(
    server_app, rows_in_store, role, expected
):
    async with _client(server_app, role) as client:
        response = await client.get("/api/admin/logs/errors")
    assert response.status_code == expected


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.super_admin, 200),
        (UserRole.admin, 200),
        (UserRole.manager, 403),
        (UserRole.user, 403),
    ],
)
async def test_only_platform_admins_can_download(
    server_app, rows_in_store, audit_calls, monkeypatch, role, expected
):
    async def _export(session, **kwargs):
        return [], False

    monkeypatch.setattr(error_events, "export_error_events", _export)
    async with _client(server_app, role) as client:
        response = await client.get("/api/admin/logs/download?format=json")
    assert response.status_code == expected


async def test_unauthenticated_requests_are_rejected(server_app):
    async with _client(server_app, None) as client:
        for path in ("/api/admin/logs/errors", "/api/admin/logs/download"):
            response = await client.get(path)
            assert response.status_code == 401, path


# ---------------------------------------------------------------------------
# Listing, lookup and redaction
# ---------------------------------------------------------------------------


async def test_list_response_is_redacted_and_uses_route_templates(
    server_app, rows_in_store
):
    async with _client(server_app, UserRole.admin) as client:
        response = await client.get("/api/admin/logs/errors?status=500")
    body = response.text
    assert response.status_code == 200
    assert EMAIL not in body
    assert SECRET_TOKEN not in body
    assert "/api/omnichannel/telegram/{bot_token}/inbound" in body
    assert response.json()["total"] == 2


async def test_detail_returns_stack_and_related_log_lines(
    server_app, rows_in_store, monkeypatch, tmp_path
):
    log_file = tmp_path / "app.log"
    log_file.write_text(
        json.dumps(
            {
                "event": "request.error",
                "request_id": "req-0002-abcdef",
                "message": f"x {EMAIL}",
            }
        )
        + "\n"
        + json.dumps({"event": "request.completed", "request_id": "req-9999-zzzzzz"})
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_LOG_FILE", str(log_file))
    async with _client(server_app, UserRole.super_admin) as client:
        response = await client.get("/api/admin/logs/errors/req-0002-abcdef")
    payload = response.json()
    assert response.status_code == 200
    assert payload["log_file_configured"] is True
    assert len(payload["related_logs"]) == 1
    assert EMAIL not in response.text
    assert SECRET_TOKEN not in response.text


async def test_unknown_request_id_returns_404(server_app, rows_in_store):
    async with _client(server_app, UserRole.admin) as client:
        response = await client.get("/api/admin/logs/errors/req-missing-000")
    assert response.status_code == 404


async def test_inverted_or_oversized_ranges_are_refused(server_app, rows_in_store):
    async with _client(server_app, UserRole.admin) as client:
        inverted = await client.get(
            "/api/admin/logs/errors?start=2026-10-18T10:00:00Z&end=2026-10-18T09:00:00Z"
        )
        oversized = await client.get(
            "/api/admin/logs/errors?start=2026-01-01T00:00:00Z&end=2026-10-18T00:00:00Z"
        )
    assert inverted.status_code == 422
    assert oversized.status_code == 422


# ---------------------------------------------------------------------------
# Downloads: cap, redaction, audit
# ---------------------------------------------------------------------------


async def test_json_download_is_redacted_and_audited(
    server_app, monkeypatch, audit_calls
):
    rows = [
        _event(
            request_id="req-7001-abcdef",
            route="/api/omnichannel/telegram/{bot_token}/inbound",
            message=f"{EMAIL} sent Bearer {SECRET_TOKEN}",
            stack=f"File app/x.py line 3 token={SECRET_TOKEN}",
        )
    ]

    async def _export(session, **kwargs):
        return rows, False

    monkeypatch.setattr(error_events, "export_error_events", _export)
    async with _client(server_app, UserRole.admin) as client:
        response = await client.get("/api/admin/logs/download?format=json&status=500")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert response.headers["x-row-cap"] == "10000"
    assert response.headers["x-truncated"] == "false"
    body = response.text
    assert EMAIL not in body
    assert SECRET_TOKEN not in body
    assert "/api/omnichannel/telegram/{bot_token}/inbound" in body
    assert json.loads(body)["items"][0]["request_id"] == "req-7001-abcdef"

    assert len(audit_calls) == 1
    action, details = audit_calls[0]
    assert action == "download"
    assert details["resource"] == "error_logs"
    assert details["user_id"] == "00000000-0000-4000-8000-0000000000aa"
    assert details["meta"]["format"] == "json"
    assert details["meta"]["row_count"] == 1


async def test_csv_download_neutralises_formulas_and_redacts(
    server_app, monkeypatch, audit_calls
):
    rows = [_event(request_id="req-7002-abcdef", message=f'=HYPERLINK("x") {EMAIL}')]

    async def _export(session, **kwargs):
        return rows, False

    monkeypatch.setattr(error_events, "export_error_events", _export)
    async with _client(server_app, UserRole.super_admin) as client:
        response = await client.get("/api/admin/logs/download?format=csv")

    lines = response.text.strip().splitlines()
    assert response.headers["content-type"].startswith("text/csv")
    assert lines[0].startswith("occurred_at,request_id,method,route,status_code")
    assert "'=HYPERLINK" in lines[1]
    assert EMAIL not in response.text
    assert audit_calls[0][1]["meta"]["format"] == "csv"


async def test_download_is_capped_at_ten_thousand_rows(
    server_app, monkeypatch, audit_calls
):
    rows = [
        _event(request_id=f"req-{i:08d}") for i in range(error_events.EXPORT_ROW_CAP)
    ]

    async def _export(session, **kwargs):
        return rows, True

    monkeypatch.setattr(error_events, "export_error_events", _export)
    async with _client(server_app, UserRole.admin) as client:
        response = await client.get("/api/admin/logs/download?format=json")

    payload = response.json()
    assert len(payload["items"]) == 10_000
    assert payload["truncated"] is True
    assert response.headers["x-truncated"] == "true"
    assert audit_calls[0][1]["meta"]["truncated"] is True


async def test_export_query_applies_the_row_cap_in_sql():
    session = _ExportSession([])
    await error_events.export_error_events(
        session,
        start=datetime(2026, 10, 1, tzinfo=timezone.utc),
        end=datetime(2026, 10, 2, tzinfo=timezone.utc),
    )
    sql = str(
        session.statements[0].compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert f"LIMIT {error_events.EXPORT_ROW_CAP + 1}" in sql


async def test_export_service_trims_to_cap_and_reports_truncation():
    rows = [
        _event(request_id=f"req-{i:08d}")
        for i in range(error_events.EXPORT_ROW_CAP + 1)
    ]
    kept, truncated = await error_events.export_error_events(
        _ExportSession(rows), start=None, end=None
    )
    assert len(kept) == error_events.EXPORT_ROW_CAP
    assert truncated is True


# ---------------------------------------------------------------------------
# Error capture: a 500 writes a row whose request ID matches the response header
# ---------------------------------------------------------------------------


async def test_unhandled_500_is_recorded_with_matching_request_id(
    server_app, persisted, monkeypatch
):
    async def _ctx() -> PlatformContext:
        return _context(UserRole.admin)

    async def _broken_db():
        raise RuntimeError(f"connection refused for {EMAIL} token={SECRET_TOKEN}")
        yield  # pragma: no cover

    server_app.dependency_overrides[get_current_platform_context] = _ctx
    server_app.dependency_overrides[get_db] = _broken_db
    async with AsyncClient(
        transport=ASGITransport(app=server_app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/admin/logs/errors", headers={"X-Request-Id": "req-live-500-0001"}
        )

    assert response.status_code == 500
    assert response.headers["x-request-id"] == "req-live-500-0001"
    assert response.json()["requestId"] == "req-live-500-0001"
    assert "Traceback" not in response.text

    assert len(persisted) == 1
    record = persisted[0]
    assert record.request_id == "req-live-500-0001"
    assert record.status_code == 500
    assert record.route == "/api/admin/logs/errors"
    assert record.exception_type == "RuntimeError"
    assert record.release_version
    assert record.actor_hash is None or record.actor_hash.startswith("sha256:")
    assert EMAIL not in (record.message or "")
    assert SECRET_TOKEN not in (record.message or "")
    assert SECRET_TOKEN not in (record.stack_trace or "")


def _probe_app() -> FastAPI:
    app = FastAPI()
    install_request_context(app)

    @app.get("/api/shares/{share_token}")
    async def share(share_token: str, token: str = ""):
        raise ValueError(f"no share for {EMAIL} at /api/shares/{share_token}")

    return app


async def test_probe_failure_keeps_token_out_of_stored_record(persisted):
    app = _probe_app()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            f"/api/shares/{SECRET_TOKEN}?token={SECRET_TOKEN}",
        )
    assert response.status_code == 500
    record = persisted[0]
    assert record.route == "/api/shares/{share_token}"
    assert record.request_id == response.headers["x-request-id"]
    assert SECRET_TOKEN not in (record.message or "")
    assert SECRET_TOKEN not in (record.stack_trace or "")
    assert EMAIL not in (record.message or "")


async def test_caller_request_id_is_honoured_only_when_well_formed(persisted):
    app = _probe_app()
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/shares/abc", headers={"X-Request-Id": "bad id\nINJECT"}
        )
    returned = response.headers["x-request-id"]
    assert returned != "bad id\nINJECT"
    assert safe_request_id(returned) == returned
    assert persisted[0].request_id == returned


# ---------------------------------------------------------------------------
# Retention and migration
# ---------------------------------------------------------------------------


class _DeleteSession:
    def __init__(self, rowcount):
        self.rowcount = rowcount
        self.statements = []
        self.commits = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        return SimpleNamespace(rowcount=self.rowcount)

    async def commit(self):
        self.commits += 1


async def test_prune_deletes_events_older_than_thirty_days():
    session = _DeleteSession(rowcount=3)
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    removed = await ops_service.prune_error_events(session, now=now)
    assert removed == 3
    assert session.commits == 1
    sql = str(
        session.statements[0].compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    assert "error_events" in sql
    assert "2026-09-18" in sql  # cutoff is exactly thirty days before ``now``
    assert ops_service.ERROR_EVENT_RETENTION_DAYS == 30


def test_error_events_revision_follows_0059():
    # Other migrations may be stacked on top of this one, so this checks that the
    # revision sits on 0059 and is reachable from the heads, not that it is a head.
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    script = ScriptDirectory.from_config(config)
    revision = script.get_revision("0060_error_events")
    assert revision.down_revision == "0059_admin_config_overrides"
    reachable = {r.revision for r in script.walk_revisions()}
    assert "0060_error_events" in reachable


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def test_scrub_text_removes_personal_and_credential_data():
    text = (
        f"user {EMAIL} call https://x.test/share/abc?token={SECRET_TOKEN}&n=1 "
        "Authorization: Bearer abc.def.ghi123 "
        "jwt eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl "
        "key sk_live_ABCDEFGH12345678"
    )
    cleaned = scrub_text(text)
    assert EMAIL not in cleaned
    assert SECRET_TOKEN not in cleaned
    assert "abc.def.ghi123" not in cleaned
    assert "eyJhbGciOi" not in cleaned
    assert "sk_live_ABCDEFGH12345678" not in cleaned
    assert "x.test/share/abc?[redacted]" in cleaned


def test_scrub_text_limits_length():
    assert len(scrub_text("a" * 1000, limit=300)) == 300


def test_replace_raw_path_swaps_concrete_path_for_template():
    text = "failed at /api/omnichannel/telegram/123:SECRET/inbound"
    assert "123:SECRET" not in replace_raw_path(
        text,
        "/api/omnichannel/telegram/123:SECRET/inbound",
        "/api/omnichannel/telegram/{bot_token}/inbound",
    )


def test_format_frames_keeps_innermost_frames_without_source_text():
    frames = [(f"C:\\deploy\\app\\dir{i}\\mod.py", i, f"fn{i}") for i in range(20)]
    lines = format_frames(frames, max_frames=3)
    assert len(lines) == 3
    assert lines[-1] == "app/dir19/mod.py:19 in fn19"


def test_safe_request_id_rejects_injection_and_keeps_plain_tokens():
    assert safe_request_id("req-abc-12345") == "req-abc-12345"
    replaced = safe_request_id("short")
    assert replaced != "short" and len(replaced) == 36


def test_processor_stamps_request_fields_on_every_line():
    scope = {
        "method": "POST",
        "route": SimpleNamespace(path="/api/widgets/{widget_id}"),
        "state": {"actor_hash": "sha256:aaaa", "org_hash": "sha256:bbbb"},
    }
    token = request_context._CURRENT.set(
        {"scope": scope, "request_id": "req-proc-000001"}
    )
    try:
        line = request_context.add_request_context(None, "info", {"event": "x"})
    finally:
        request_context._CURRENT.reset(token)
    assert line["request_id"] == "req-proc-000001"
    assert line["route"] == "/api/widgets/{widget_id}"
    assert line["method"] == "POST"
    assert line["actor_hash"] == "sha256:aaaa"
    assert line["org_hash"] == "sha256:bbbb"


def test_related_log_lines_are_filtered_and_scrubbed(tmp_path):
    path = tmp_path / "app.log"
    path.write_text(
        json.dumps(
            {
                "event": "request.error",
                "request_id": "req-abc-12345",
                "message": f"failed for {EMAIL} token={SECRET_TOKEN}",
            }
        )
        + "\n"
        + json.dumps({"event": "request.completed", "request_id": "req-other-999"})
        + "\n",
        encoding="utf-8",
    )
    found = error_events.read_related_log_lines("req-abc-12345", str(path))
    assert len(found) == 1
    blob = json.dumps(found)
    assert EMAIL not in blob
    assert SECRET_TOKEN not in blob


def test_serialize_drops_stack_unless_requested():
    row = _event(message="boom", stack="File x line 1")
    assert "stack_trace" not in error_events.serialize_error_event(row)
    assert error_events.serialize_error_event(row, include_stack=True)[
        "stack_trace"
    ] == ("File x line 1")


def test_build_error_event_scrubs_before_storage():
    try:
        raise RuntimeError(f"no user {EMAIL} for {SECRET_TOKEN}")
    except RuntimeError as exc:
        data = error_events.build_error_event(
            request_id="req-build-0001",
            method="GET",
            route="/api/shares/{share_token}",
            status_code=500,
            duration_ms=5,
            exc=exc,
            raw_path=f"/api/shares/{SECRET_TOKEN}",
        )
    assert EMAIL not in data["message"]
    assert SECRET_TOKEN not in data["message"]
    assert SECRET_TOKEN not in data["stack_trace"]
    assert data["exception_type"] == "RuntimeError"
    assert data["occurred_at"].tzinfo is not None


def test_retention_window_is_applied_relative_to_now():
    now = datetime(2026, 10, 18, tzinfo=timezone.utc)
    assert now - timedelta(days=ops_service.ERROR_EVENT_RETENTION_DAYS) == datetime(
        2026, 9, 18, tzinfo=timezone.utc
    )
