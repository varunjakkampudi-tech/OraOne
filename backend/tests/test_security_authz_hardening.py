"""Security hardening: write-route authorization, log hygiene, upload limits, AI rate tier.

No database, network or real storage: routes run through TestClient with
dependency overrides and a null session. The permission gate runs before any
handler body, so a 403 proves the gate and a non-403 proves the caller got past it.
"""

from __future__ import annotations

import asyncio
import importlib
import io
import os
import uuid
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.super_admin.deps import get_platform_admin
from app.core.log_redaction import fingerprint, redact_email
from app.core.permissions import Permission, has_permission
from app.database.session import get_db
from app.middleware.access_log import UNMATCHED_ROUTE, route_template
from app.middleware.org_context import OrgContext, get_current_organization
from app.middleware.project_context import ProjectContext, get_current_project
from app.middleware.rate_limit import TIERS
from app.middleware.upload_size_limit import UploadSizeLimitMiddleware
from app.services import upload_limits
from app.services.upload_limits import (
    READ_CHUNK_BYTES,
    assert_office_package_safe,
    read_capped,
)

ORG = uuid.uuid4()
PROJECT = uuid.uuid4()
USER = uuid.uuid4()

# (module, endpoint function, permission the route now requires).
# Viewers hold CHAT_USE and KB_READ by design, so those routes are not 403 for them.
CHANGED_WRITE_ROUTES = [
    ("app.api.agent_versioning.routes", "publish_version", "AGENTS_WRITE"),
    ("app.api.agent_versioning.routes", "restore_version", "AGENTS_WRITE"),
    ("app.api.agents.routes", "create_agent", "AGENTS_WRITE"),
    ("app.api.agents.routes", "update_agent", "AGENTS_WRITE"),
    ("app.api.ai_models.routes", "clarify_agent", "AGENTS_WRITE"),
    ("app.api.assistants.routes", "run_assistant", "CHAT_USE"),
    ("app.api.channels.routes", "update_domains", "AGENTS_WRITE"),
    ("app.api.channels.routes", "publish_deploy", "AGENTS_WRITE"),
    ("app.api.channels.routes", "verify_deploy", "AGENTS_WRITE"),
    ("app.api.chat.folders", "create_folder", "CHAT_USE"),
    ("app.api.chat.folders", "update_folder", "CHAT_USE"),
    ("app.api.chat.folders", "delete_folder", "CHAT_USE"),
    ("app.api.chat.routes", "create_conversation", "CHAT_USE"),
    ("app.api.chat.routes", "rename_conversation", "CHAT_USE"),
    ("app.api.chat.routes", "delete_conversation", "CHAT_USE"),
    ("app.api.chat.routes", "patch_conversation", "CHAT_USE"),
    ("app.api.chat.routes", "enable_share", "CHAT_USE"),
    ("app.api.chat.routes", "disable_share", "CHAT_USE"),
    ("app.api.chat.routes", "regenerate_last", "CHAT_USE"),
    ("app.api.chat.routes", "send_message", "CHAT_USE"),
    ("app.api.chat.routes", "stream_message", "CHAT_USE"),
    ("app.api.collaboration.routes", "share_resource", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "unshare_resource", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "create_comment", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "resolve_comment", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "toggle_reaction", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "mark_notification_read", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "mark_all_read", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "create_task", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "update_task", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "follow_resource", "COLLAB_WRITE"),
    ("app.api.collaboration.routes", "unfollow_resource", "COLLAB_WRITE"),
    ("app.api.entitlements", "request_access", "BILLING_MANAGE"),
    ("app.api.feature_requests.routes", "create_feature_request", "COLLAB_WRITE"),
    ("app.api.feature_requests.routes", "toggle_vote", "COLLAB_WRITE"),
    ("app.api.feature_requests.routes", "delete_feature_request", "COLLAB_WRITE"),
    ("app.api.knowledge.organization", "create_knowledge_folder", "KB_WRITE"),
    ("app.api.knowledge.organization", "update_knowledge_folder", "KB_WRITE"),
    ("app.api.knowledge.organization", "delete_knowledge_folder", "KB_DELETE"),
    ("app.api.knowledge.organization", "patch_document", "KB_WRITE"),
    ("app.api.knowledge.organization", "bulk_documents", "KB_WRITE"),
    ("app.api.knowledge.organization", "knowledge_search", "KB_READ"),
    ("app.api.knowledge.routes", "create_knowledge_base", "KB_WRITE"),
    ("app.api.knowledge.routes", "update_knowledge_base", "KB_WRITE"),
    ("app.api.knowledge.routes", "upload_document", "KB_WRITE"),
    ("app.api.knowledge.routes", "process_document_endpoint", "KB_WRITE"),
    ("app.api.knowledge.sources", "ingest_website", "KB_WRITE"),
    ("app.api.knowledge.sources", "ingest_text", "KB_WRITE"),
    ("app.api.operations.routes", "security_scan", "CHAT_USE"),
    ("app.api.operations.routes", "security_mask", "CHAT_USE"),
    ("app.api.rag.routes", "rag_query", "KB_READ"),
    ("app.api.rag.routes", "rag_search", "KB_READ"),
    ("app.api.v2.routes", "create_conversation", "CHAT_USE"),
    ("app.api.v2.routes", "create_message", "CHAT_USE"),
    ("app.api.websites.routes", "create_website", "KB_WRITE"),
    ("app.api.websites.routes", "update_website", "KB_WRITE"),
    ("app.api.websites.routes", "crawl_website", "KB_WRITE"),
    ("app.api.websites.routes", "recrawl_website", "KB_WRITE"),
    ("app.api.websites.routes", "pause_website", "KB_WRITE"),
    ("app.api.websites.routes", "resume_website", "KB_WRITE"),
    ("app.api.websites.routes", "cancel_website", "KB_WRITE"),
    ("app.api.workspace_intel.routes", "run_simulator", "AGENTS_WRITE"),
]

ROUTE_IDS = [f"{'.'.join(m.split('.')[-2:])}.{f}" for m, f, _ in CHANGED_WRITE_ROUTES]


class _Empty:
    rowcount = 0

    def all(self):
        return []

    def first(self):
        return None

    def one_or_none(self):
        return None

    def __iter__(self):
        return iter(())


class _NullSession:
    """Answers every query with nothing, so handlers never reach real storage."""

    async def scalar(self, *_a, **_k):
        return None

    async def scalars(self, *_a, **_k):
        return _Empty()

    async def execute(self, *_a, **_k):
        return _Empty()

    async def get(self, *_a, **_k):
        return None

    def add(self, *_a, **_k):
        return None

    async def flush(self):
        return None

    async def commit(self):
        return None

    async def rollback(self):
        return None

    async def refresh(self, *_a, **_k):
        return None

    async def delete(self, *_a, **_k):
        return None


def _endpoint(module_name: str, func_name: str):
    """Return (router, route) for a module-level endpoint function."""
    module = importlib.import_module(module_name)
    fn = getattr(module, func_name)
    for value in vars(module).values():
        if isinstance(value, APIRouter):
            for route in value.routes:
                if getattr(route, "endpoint", None) is fn:
                    return value, route
    raise LookupError(f"{module_name}.{func_name} is not a registered route")


def _client(router: APIRouter, role: str) -> TestClient:
    async def _org():
        return OrgContext(
            user_id=USER, auth_subject="sub", organization_id=ORG, membership_role=role
        )

    async def _project():
        return ProjectContext(
            user_id=USER,
            organization_id=ORG,
            membership_role=role,
            project_id=PROJECT,
            project_slug="default",
            is_default_project=True,
        )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_organization] = _org
    app.dependency_overrides[get_current_project] = _project
    app.dependency_overrides[get_db] = lambda: _NullSession()
    return TestClient(app, raise_server_exceptions=False)


def _concrete_path(template: str) -> str:
    out = template
    while "{" in out:
        start = out.index("{")
        end = out.index("}", start)
        out = out[:start] + str(uuid.uuid4()) + out[end + 1 :]
    return out


def _send(client: TestClient, route):
    method = next(iter(route.methods - {"HEAD"}))
    return client.request(method, _concrete_path(route.path), json={})


# ───────────────────── write routes: viewer / member / admin ─────────────────────


@pytest.mark.parametrize(
    ("module", "func", "perm"), CHANGED_WRITE_ROUTES, ids=ROUTE_IDS
)
def test_viewer_is_refused_on_permissioned_write_routes(module, func, perm):
    router, route = _endpoint(module, func)
    response = _send(_client(router, "viewer"), route)
    if has_permission("viewer", getattr(Permission, perm)):
        # Viewers hold this permission by design (chat and read-only search).
        assert response.status_code != 403, response.text
    else:
        assert response.status_code == 403, response.text
        assert "lacks required permission" in response.text


@pytest.mark.parametrize(
    ("module", "func", "perm"), CHANGED_WRITE_ROUTES, ids=ROUTE_IDS
)
def test_admin_passes_the_gate_on_every_changed_route(module, func, perm):
    router, route = _endpoint(module, func)
    response = _send(_client(router, "admin"), route)
    assert response.status_code not in (401, 403), response.text


def test_member_is_permitted_on_builder_routes_and_refused_on_admin_only_ones():
    for module, func, perm in CHANGED_WRITE_ROUTES:
        router, route = _endpoint(module, func)
        response = _send(_client(router, "member"), route)
        if has_permission("member", getattr(Permission, perm)):
            assert response.status_code not in (401, 403), (func, response.text)
        else:
            assert response.status_code == 403, (func, response.text)


# ───────────────────── usage recording: platform admins only ─────────────────────


def _usage_client(*, platform_admin: bool, monkeypatch) -> TestClient:
    from app.api.usage import routes as usage_routes

    router, _route = _endpoint("app.api.usage.routes", "record_usage")

    async def _admin():
        if not platform_admin:
            raise HTTPException(403, "Platform administrator access required.")
        return SimpleNamespace(user_id=USER)

    monkeypatch.setattr(
        usage_routes.usage_service, "record_usage", AsyncMock(return_value=7)
    )
    client = _client(router, "owner")
    client.app.dependency_overrides[get_platform_admin] = _admin
    return client


def test_usage_record_refuses_tenant_owner_without_platform_role(monkeypatch):
    client = _usage_client(platform_admin=False, monkeypatch=monkeypatch)
    response = client.post(
        "/api/usage/record", json={"metric": "messages", "amount": 1}
    )
    assert response.status_code == 403


def test_usage_record_accepts_platform_admin(monkeypatch):
    client = _usage_client(platform_admin=True, monkeypatch=monkeypatch)
    response = client.post(
        "/api/usage/record", json={"metric": "messages", "amount": 1}
    )
    assert response.status_code == 200, response.text
    assert response.json()["period_total"] == 7


# ───────────────────── access logs never carry path-borne tokens ─────────────────────


def test_route_template_replaces_path_tokens_with_placeholders():
    from app.api.chat.folders import public_chat_router
    from app.api.omnichannel import routes as omnichannel_routes

    app = FastAPI()
    app.include_router(omnichannel_routes.router)
    app.include_router(public_chat_router)
    # Route handlers must not reach the process-wide database engine, whose
    # connection pool may be bound to an event loop closed by an earlier test.
    app.dependency_overrides[get_db] = lambda: _NullSession()
    seen: dict[str, str] = {}

    @app.middleware("http")
    async def _record(request, call_next):
        response = await call_next(request)
        seen[request.url.path] = route_template(request.scope)
        return response

    client = TestClient(app, raise_server_exceptions=False)
    telegram = "/api/channels/telegram/123456789:AAFakeBotToken/inbound"
    share = "/api/public/conversations/abc123SECRET"
    client.post(telegram, json={})
    client.get(share)
    client.get("/nope/SECRET")
    assert seen[telegram] == "/api/channels/telegram/{token}/inbound"
    assert seen[share] == "/api/public/conversations/{token}"
    assert seen["/nope/SECRET"] == UNMATCHED_ROUTE


def test_access_log_never_contains_a_token_in_a_path(monkeypatch):
    import server

    recorded: list[tuple[str, dict]] = []

    class _Recorder:
        def info(self, event, **fields):
            recorded.append((event, fields))

        def error(self, event, **fields):
            recorded.append((event, fields))

    from app.core import logging as core_logging

    # The access line is written through app.core.logging.access_logger (see
    # app/middleware/request_context.py), so that is the logger to replace.
    monkeypatch.setattr(core_logging, "access_logger", _Recorder())
    monkeypatch.setitem(server.app.dependency_overrides, get_db, lambda: _NullSession())
    client = TestClient(server.app, raise_server_exceptions=False)

    bot_token = "123456789:AAFakeBotTokenOnlyForThisTest"
    share_token = "shareTokenOnlyForThisTest987"
    client.post(f"/api/channels/telegram/{bot_token}/inbound", json={})
    client.get(f"/api/public/conversations/{share_token}")

    assert recorded, "the access log middleware did not emit anything"
    labels = {fields.get("route") for _, fields in recorded}
    assert "/api/channels/telegram/{token}/inbound" in labels
    assert "/api/public/conversations/{token}" in labels
    for event, fields in recorded:
        dumped = repr((event, fields))
        assert bot_token not in dumped
        assert "AAFakeBotToken" not in dumped
        assert share_token not in dumped
        assert "ip" not in fields


def test_email_and_subject_identifiers_are_fingerprinted():
    assert redact_email("Jane.Doe@Example.com") == redact_email(
        " jane.doe@example.com "
    )
    assert "@" not in redact_email("Jane.Doe@Example.com")
    assert "jane" not in redact_email("Jane.Doe@Example.com")
    assert fingerprint(None) == "none"
    assert fingerprint("user-subject-1").startswith("sha256:")


# ───────────────────── uploads: SVG refused, capped reads, zip bombs ─────────────────────


def test_svg_brand_upload_is_refused_before_storage(monkeypatch):
    from app.api.branding import routes as branding

    stored: list[dict] = []
    monkeypatch.setattr(branding.storage, "put_object", lambda **kw: stored.append(kw))
    client = _client(branding.router, "owner")
    response = client.post(
        "/api/branding/logo",
        files={"file": ("logo.svg", b"<svg onload='alert(1)'/>", "image/svg+xml")},
    )
    assert response.status_code == 415, response.text
    assert stored == []
    assert "image/svg+xml" not in branding._ALLOWED_IMAGE_TYPES


class _CountingUpload:
    """Serves an endless stream and records how much the reader pulled."""

    filename = "huge.pdf"

    def __init__(self) -> None:
        self.served = 0

    async def read(self, size: int = -1) -> bytes:
        size = READ_CHUNK_BYTES if size is None or size < 0 else size
        self.served += size
        return b"x" * size


def test_oversize_upload_is_refused_without_reading_it_all():
    upload = _CountingUpload()
    cap = 5 * 1024 * 1024
    with pytest.raises(HTTPException) as exc:
        asyncio.run(read_capped(upload, cap))
    assert exc.value.status_code == 413
    assert upload.served <= cap + READ_CHUNK_BYTES


def test_declared_oversize_request_is_rejected_before_the_app_runs():
    called: list[str] = []

    async def inner_app(scope, receive, send):
        called.append(scope["path"])

    sent: list[dict] = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/documents/upload",
        "headers": [(b"content-length", str(40 * 1024 * 1024).encode())],
    }
    asyncio.run(UploadSizeLimitMiddleware(inner_app)(scope, receive, send))
    assert called == []
    assert sent[0]["status"] == 413


def test_declared_small_request_reaches_the_app():
    called: list[bool] = []

    async def inner_app(scope, receive, send):
        called.append(True)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(_message):
        return None

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/documents/upload",
        "headers": [(b"content-length", b"1024")],
    }
    asyncio.run(UploadSizeLimitMiddleware(inner_app)(scope, receive, send))
    assert called == [True]


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_zip_bomb_docx_is_refused():
    # 50 MB of zeros compresses to a few tens of KB: a classic expansion bomb.
    bomb = _zip_bytes({"word/document.xml": b"\x00" * (50 * 1024 * 1024)})
    assert len(bomb) < 1024 * 1024
    with pytest.raises(HTTPException) as exc:
        assert_office_package_safe("report.docx", bomb)
    assert exc.value.status_code == 413


def test_total_uncompressed_cap_applies_to_office_packages():
    payload = os.urandom(
        2 * 1024 * 1024
    )  # incompressible, so the ratio check stays quiet
    package = _zip_bytes({"xl/data.bin": payload})
    with pytest.raises(HTTPException) as exc:
        assert_office_package_safe("sheet.xlsx", package, max_uncompressed=1024 * 1024)
    assert exc.value.status_code == 413


def test_legitimate_office_package_passes_and_non_office_is_not_inspected():
    package = _zip_bytes({"word/document.xml": b"<w:document/>" * 100})
    assert_office_package_safe("notes.docx", package)
    assert_office_package_safe("archive.zip", b"not a zip at all")


def test_office_extension_with_non_zip_content_is_rejected():
    with pytest.raises(HTTPException) as exc:
        assert_office_package_safe("fake.pptx", b"plain text, not a package")
    assert exc.value.status_code == 422


def test_upload_limits_module_exposes_the_documented_caps():
    assert upload_limits.MAX_OFFICE_UNCOMPRESSED_BYTES == 100 * 1024 * 1024


# ───────────────────── AI rate-limit coverage ─────────────────────


def _tier(method: str, path: str) -> str | None:
    return next((t.name for t in TIERS if t.matches(path, method)), None)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/api/knowledge/sources/website"),
        ("POST", "/api/knowledge/sources/text"),
        ("POST", "/api/knowledge/search"),
        ("POST", "/api/ai/clarify"),
        ("POST", "/api/assistants/support/run"),
        ("POST", "/api/v2/conversations/abc/messages"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/workflows/abc/run"),
        ("POST", "/api/workspace/simulator/run"),
    ],
)
def test_model_calling_write_routes_share_the_ai_budget(method, path):
    assert _tier(method, path) == "ai"


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/knowledge/sources"),
        ("GET", "/api/v2/conversations"),
        ("GET", "/api/assistants"),
    ],
)
def test_reads_under_the_same_prefixes_keep_the_general_budget(method, path):
    assert _tier(method, path) == "api"
