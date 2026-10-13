"""Regression tests for production-only fail-closed behavior."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.mark.asyncio
async def test_readiness_requires_redis_in_production(monkeypatch):
    from app.api import health

    class _Conn:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def execute(self, _query):
            return None

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setattr(
        health, "init_engine", lambda: SimpleNamespace(connect=lambda: _Conn())
    )

    with pytest.raises(Exception) as exc_info:
        await health.readiness()
    assert getattr(exc_info.value, "status_code", None) == 503
    assert exc_info.value.detail["checks"]["redis"] == "not_configured"


def test_google_drive_real_mode_never_returns_mock_documents(monkeypatch):
    from app.connectors.google_drive import GoogleDriveConnector
    from app.connectors.base import NotConnectedError
    from app.database.models.integration import ConnectionType

    integration = SimpleNamespace(
        connection_type=ConnectionType.oauth,
        access_token=None,
        refresh_token=None,
        config={},
    )
    connector = GoogleDriveConnector(integration)
    monkeypatch.setattr(
        "app.connectors.google_drive.crypto.decrypt", lambda value: None
    )

    with pytest.raises(NotConnectedError):
        connector.sync()
    with pytest.raises(NotConnectedError):
        connector.browse()


def test_google_drive_mock_mode_is_disabled_in_production(monkeypatch):
    from app.connectors.google_drive import GoogleDriveConnector
    from app.connectors.base import NotConnectedError
    from app.database.models.integration import ConnectionType

    monkeypatch.setenv("ENVIRONMENT", "production")
    integration = SimpleNamespace(
        connection_type=ConnectionType.mock,
        access_token=None,
        refresh_token=None,
        config={},
    )
    connector = GoogleDriveConnector(integration)

    with pytest.raises(NotConnectedError):
        connector.sync()
