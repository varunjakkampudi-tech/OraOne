"""The development password sign-in must be unreachable outside development."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.schemas.auth import LoginRequest
from app.services import auth_service


async def _attempt_login(monkeypatch, *, environment: str, flag: str | None):
    """Call the development login with the given environment and flag values."""
    monkeypatch.setattr(auth_service.settings, "environment", environment)
    if flag is None:
        monkeypatch.delenv("ALLOW_DEV_PASSWORD_LOGIN", raising=False)
    else:
        monkeypatch.setenv("ALLOW_DEV_PASSWORD_LOGIN", flag)
    return await auth_service.dev_password_login(
        session=None, data=LoginRequest(email="a@b.com", password="whatever")
    )


@pytest.mark.asyncio
async def test_dev_login_is_disabled_by_default(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await _attempt_login(monkeypatch, environment="development", flag=None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_dev_login_is_refused_in_production_even_with_flag(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await _attempt_login(monkeypatch, environment="production", flag="true")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_dev_login_is_refused_in_staging_even_with_flag(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await _attempt_login(monkeypatch, environment="staging", flag="true")
    assert exc.value.status_code == 404
