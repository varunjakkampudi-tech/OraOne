"""Regression: audit JSONB snapshots preserve real typed identifiers safely."""

import json
from collections import deque
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

import pytest

from app.services import audit as audit_service


@pytest.mark.asyncio
async def test_typed_audit_snapshots_are_json_serializable_and_detached(monkeypatch):
    class State(Enum):
        active = "active"

    pending = deque(maxlen=5000)
    monkeypatch.setattr(audit_service, "_PENDING", pending)
    identifier = uuid4()
    timestamp = datetime(2026, 10, 14, tzinfo=timezone.utc)
    snapshot = {
        "knowledge_base_ids": [identifier],
        "state": State.active,
        "at": timestamp,
    }
    audit_service.audit(
        "update",
        resource="agent",
        organization_id=str(uuid4()),
        user_id=str(uuid4()),
        after=snapshot,
    )
    snapshot["knowledge_base_ids"].clear()

    class Session:
        def add_all(self, rows):
            self.rows = rows

        async def commit(self):
            for row in self.rows:
                json.dumps(row.after)

        async def rollback(self):
            pass

    session = Session()
    assert await audit_service.flush_pending(session) == 1
    assert session.rows[0].after == {
        "knowledge_base_ids": [str(identifier)],
        "state": "active",
        "at": timestamp.isoformat(),
    }
    assert not pending
