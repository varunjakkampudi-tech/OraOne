"""Regression: workspace write routes must enforce the RBAC permission matrix.

A live verifier showed an invited `viewer` could create/update agents because
these handlers only resolved organization membership, not role permission.
"""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database.session import get_db
from app.middleware.org_context import OrgContext, get_current_organization
from server import app

PROTECTED = {
    ("POST", "/api/agents"): "agents.write",
    ("PUT", "/api/agents/{agent_id}"): "agents.write",
    ("POST", "/api/agents/{agent_id}/versions"): "agents.write",
    ("POST", "/api/agents/{agent_id}/versions/restore"): "agents.write",
    ("PATCH", "/api/agents/{agent_id}/channels/{channel}"): "agents.write",
    ("POST", "/api/knowledge-bases"): "kb.write",
    ("PUT", "/api/knowledge-bases/{kb_id}"): "kb.write",
    ("POST", "/api/documents/upload"): "kb.write",
    ("POST", "/api/documents/{document_id}/process"): "kb.write",
    ("PATCH", "/api/documents/{document_id}"): "kb.write",
    ("POST", "/api/documents/bulk"): "kb.write",
    ("POST", "/api/knowledge-folders"): "kb.write",
    ("PUT", "/api/knowledge-folders/{folder_id}"): "kb.write",
    ("DELETE", "/api/knowledge-folders/{folder_id}"): "kb.delete",
    ("POST", "/api/knowledge/sources/website"): "kb.write",
    ("POST", "/api/knowledge/sources/text"): "kb.write",
    ("POST", "/api/websites"): "kb.write",
    ("PUT", "/api/websites/{website_id}"): "kb.write",
    ("POST", "/api/websites/{website_id}/crawl"): "kb.write",
    ("POST", "/api/websites/{website_id}/recrawl"): "kb.write",
    ("POST", "/api/websites/{website_id}/pause"): "kb.write",
    ("POST", "/api/websites/{website_id}/resume"): "kb.write",
    ("POST", "/api/websites/{website_id}/cancel"): "kb.write",
    ("POST", "/api/leads"): "leads.write",
    ("PATCH", "/api/leads/{lead_id}"): "leads.write",
    ("DELETE", "/api/leads/{lead_id}"): "leads.write",
    ("POST", "/api/usage/record"): "settings.manage",
}


def _ctx(role):
    return OrgContext(
        user_id=uuid.uuid4(),
        cognito_sub="rbac-test",
        organization_id=uuid.uuid4(),
        membership_role=role,
    )


@pytest.fixture
def as_role():
    async def _no_db():
        yield None

    def _set(role):
        app.dependency_overrides[get_current_organization] = lambda: _ctx(role)
        app.dependency_overrides[get_db] = _no_db
        return TestClient(app, raise_server_exceptions=False)

    yield _set
    app.dependency_overrides.clear()


def _url(path):
    return re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)


@pytest.mark.parametrize(("method", "path"), sorted(PROTECTED))
def test_viewer_is_denied_write_route(as_role, method, path):
    client = as_role("viewer")
    response = client.request(method, _url(path), json={})
    assert response.status_code == 403, response.text
    assert PROTECTED[(method, path)] in response.text


def test_viewer_role_is_read_only_for_guarded_permissions():
    from app.core.permissions import has_permission

    for perm in set(PROTECTED.values()):
        assert not has_permission("viewer", perm)
    for perm in ("agents.write", "kb.write", "leads.write"):
        assert has_permission("member", perm)


@pytest.mark.parametrize(
    ("method", "path"), [("POST", "/api/leads"), ("POST", "/api/agents")]
)
def test_member_passes_permission_gate(as_role, method, path):
    response = as_role("member").request(method, _url(path), json={})
    assert response.status_code != 403
