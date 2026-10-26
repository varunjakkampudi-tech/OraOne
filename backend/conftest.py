"""Load .env for pytest before any `app.*` modules are imported.

`app.core.config` raises at import time if `JWT_SECRET_KEY` isn't set (or is
too short). We want pytest to find it in `backend/.env` just like uvicorn
does at server start.
"""

from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env", override=False)

# ── AI budget defaults ──────────────────────────────────────────────────────
# Most tests run without a database. By default a reservation succeeds and
# settlement does nothing. Budget tests use the real functions kept below.
from app.services import usage_service as _usage_service  # noqa: E402

REAL_RESERVE_METERED = _usage_service.reserve_metered
REAL_SETTLE_METERED = _usage_service.settle_metered


@pytest.fixture(autouse=True)
def _ai_budget_allows_by_default(monkeypatch):
    async def _reserve(*_args, **_kwargs):
        return True

    async def _settle(*_args, **_kwargs):
        return None

    monkeypatch.setattr(_usage_service, "reserve_metered", _reserve)
    monkeypatch.setattr(_usage_service, "settle_metered", _settle)


@pytest.fixture(autouse=True)
def _no_live_mail_provider(monkeypatch):
    """Tests never reach the mail provider.

    A developer machine may have a real Resend key in its environment. Clearing it
    here means no test can send email; tests that exercise Resend pass an explicit
    stub or a mock transport.
    """
    from app.core.config import settings

    monkeypatch.setattr(settings, "resend_api_key", "")
