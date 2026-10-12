"""OAuth state transaction binding and replay protection."""

import uuid

import pytest


def test_oauth_state_is_single_use(monkeypatch):
    from app.api.integrations import routes

    monkeypatch.setenv("SECRET_KEY", "test-oauth-state-secret-32-bytes!!")
    monkeypatch.setenv("ENVIRONMENT", "development")
    from app.services import cache

    cache._namespaced_singletons.clear()
    token = routes.issue_oauth_state(
        provider="google_drive",
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )

    claims = routes.verify_oauth_state(token)
    assert claims["provider"] == "google_drive"
    with pytest.raises(routes.JWTError):
        routes.verify_oauth_state(token)
