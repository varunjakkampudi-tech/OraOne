"""Fail-closed behaviour: when a limit or store cannot confirm an action, the action is refused.

Each case below replaces one dependency with a failing version and checks that
the caller gets a refusal, not a silent success.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.services import usage_service


@pytest.mark.asyncio
async def test_exhausted_plan_quota_blocks_the_action(monkeypatch):
    async def _over_limit(*_args, **_kwargs):
        return {"allowed": False, "used": 100, "limit": 100}

    monkeypatch.setattr(usage_service, "check_quota", _over_limit)

    with pytest.raises(HTTPException) as exc:
        await usage_service.enforce_quota(None, uuid.uuid4(), "ai_messages")
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_unavailable_usage_store_does_not_allow_the_action(monkeypatch):
    async def _broken(*_args, **_kwargs):
        raise ConnectionError("usage store unreachable")

    monkeypatch.setattr(usage_service, "check_quota", _broken)

    with pytest.raises(ConnectionError):
        await usage_service.enforce_quota(None, uuid.uuid4(), "ai_messages")
