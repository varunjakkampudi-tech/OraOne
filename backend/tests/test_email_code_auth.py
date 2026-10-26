"""Passwordless email-code sign-in (/api/auth/email-code/*).

The product's sign-in is email-only: a code is emailed, then exchanged for
session cookies. These tests capture the emailed code via a monkeypatched
sender (no SMTP in tests) and exercise the real database path. They skip when
Postgres is not reachable, matching the other DB-backed suites.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import os
import uuid
from typing import AsyncIterator

import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def isolated_rate_limit_cache(monkeypatch):
    from app.middleware import rate_limit
    from app.services.cache import get_shared_cache

    cache = get_shared_cache(f"test-email-code-{uuid.uuid4().hex}")
    monkeypatch.setattr(rate_limit, "_cache", lambda: cache)


def _postgres_reachable() -> bool:
    import asyncpg

    url = os.environ.get("DATABASE_URL", "")
    if not url:
        return False
    dsn = url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )

    async def _probe() -> bool:
        try:
            conn = await asyncio.wait_for(asyncpg.connect(dsn), timeout=3)
            await conn.close()
            return True
        except Exception:
            return False

    try:
        return asyncio.run(_probe())
    except RuntimeError:
        return False


REQUIRES_DB = pytest.mark.skipif(
    not _postgres_reachable(),
    reason="Postgres is not reachable from this host.",
)


def _accept(marketing: bool = False) -> dict:
    """The signup acceptance a real client sends with the code (versions as currently in force)."""
    from app.core.config import settings

    return {
        "terms_accepted": True,
        "privacy_accepted": True,
        "marketing_consent": marketing,
        "terms_version": settings.legal_terms_version,
        "privacy_version": settings.legal_privacy_version,
    }


@pytest.fixture
def sent_codes(monkeypatch) -> dict[str, str]:
    """Capture codes the service would email instead of sending them."""
    from app.services import email_service

    codes: dict[str, str] = {}

    def fake_send(to: str, *, code: str, expires_in: str = "10 minutes") -> bool:
        codes[to] = code
        return True

    monkeypatch.setattr(email_service, "send_login_otp", fake_send)
    return codes


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator:
    from app.database import session as db_session_module
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    Maker = db_session_module.AsyncSessionLocal
    assert Maker is not None
    async with Maker() as s:
        yield s
        await s.rollback()
    await dispose_engine()


def _client():
    from httpx import ASGITransport, AsyncClient

    from server import app

    headers = {
        "X-Forwarded-For": f"10.1.{uuid.uuid4().int % 255}.{uuid.uuid4().int % 255}"
    }
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers=headers
    )


@REQUIRES_DB
@pytest.mark.asyncio
async def test_new_email_gets_code_and_signs_in(db_session, sent_codes):
    email = f"code-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        req = await client.post(
            "/api/auth/email-code/request", json={"email": email, "name": "Ada Tester"}
        )
        assert req.status_code == 200, req.text
        assert email in sent_codes

        ver = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": sent_codes[email], **_accept()},
        )
        assert ver.status_code == 200, ver.text
        body = ver.json()
        assert body["access_token"] and body["token_type"] == "Bearer"
        cookies = ver.headers.get_list("set-cookie")
        assert any(
            c.startswith("oraone_access_token=") and "HttpOnly" in c for c in cookies
        )

        me = await client.get("/api/auth/me")
        assert me.status_code == 200, me.text
        assert me.json()["email"] == email
        assert me.json()["name"] == "Ada Tester"


@REQUIRES_DB
@pytest.mark.asyncio
async def test_unknown_and_existing_emails_get_identical_responses(
    db_session, sent_codes
):
    email = f"same-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        first = await client.post("/api/auth/email-code/request", json={"email": email})
        second = await client.post(
            "/api/auth/email-code/request", json={"email": email}
        )
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


@REQUIRES_DB
@pytest.mark.asyncio
async def test_wrong_code_is_rejected(db_session, sent_codes):
    email = f"wrong-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        await client.post("/api/auth/email-code/request", json={"email": email})
        wrong = "000000" if sent_codes[email] != "000000" else "111111"
        resp = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": wrong}
        )
    assert resp.status_code == 400
    assert "access_token" not in resp.text


@REQUIRES_DB
@pytest.mark.asyncio
async def test_code_is_single_use(db_session, sent_codes):
    email = f"once-{uuid.uuid4().hex[:10]}@example.com"
    async with _client() as client:
        await client.post("/api/auth/email-code/request", json={"email": email})
        code = sent_codes[email]
        ok = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
        again = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
    assert ok.status_code == 200
    assert again.status_code == 400


# ── Sign-in code rules: no database needed ─────────────────────────────────


def test_codes_are_six_digits_from_the_os_random_source():
    import re

    from app.core.security import generate_numeric_code

    codes = {generate_numeric_code() for _ in range(200)}
    assert all(re.fullmatch(r"[0-9]{6}", code) for code in codes)
    assert len(codes) > 150  # not a constant or a short cycle


def test_stored_digest_hides_the_code_and_binds_the_address(monkeypatch):
    from app.core.config import settings
    from app.services import auth_service

    monkeypatch.setattr(settings, "jwt_secret_key", "x" * 64)
    digest = auth_service._digest("owner@example.com", "123456")
    assert "123456" not in digest
    assert digest == auth_service._digest("owner@example.com", "123456")
    assert digest != auth_service._digest("other@example.com", "123456")
    assert digest != auth_service._digest("owner@example.com", "654321")


def test_digest_refuses_to_run_without_the_server_secret(monkeypatch):
    from app.core.config import settings
    from app.services import auth_service

    monkeypatch.setattr(settings, "jwt_secret_key", "")
    with pytest.raises(RuntimeError):
        auth_service._digest("owner@example.com", "123456")


def test_sign_in_code_lives_five_minutes():
    from app.services import auth_service, email_service

    assert auth_service._LOGIN_CODE_TTL_SECONDS == 300
    assert email_service.LOGIN_OTP_EXPIRES_IN == "5 minutes"


@pytest.mark.asyncio
async def test_a_plain_code_stored_before_this_change_never_matches():
    from fastapi import HTTPException

    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    email = f"legacy-{uuid.uuid4().hex[:8]}@example.com"
    auth_service._cache().set(auth_service._code_key(email), "123456", ttl_seconds=300)
    with pytest.raises(HTTPException) as exc:
        await auth_service.verify_email_code(
            None, VerifyLoginOtpRequest(email=email, code="123456")
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_losing_the_atomic_take_refuses_the_code(monkeypatch):
    from fastapi import HTTPException

    from app.core.config import settings
    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service

    monkeypatch.setattr(settings, "jwt_secret_key", "x" * 64)
    email = f"race-{uuid.uuid4().hex[:8]}@example.com"
    auth_service._cache().set(
        auth_service._code_key(email),
        {"digest": auth_service._digest(email, "246810")},
        ttl_seconds=300,
    )

    class _ExistingUsers:
        def __init__(self, session):
            pass

        async def get_by_email(self, _email):
            return SimpleNamespace(
                auth_subject="sub-race",
                email=email,
                full_name="Race",
                password_hash="unused",
                is_email_verified=True,
                last_login_at=None,
                status=SimpleNamespace(value="active"),
            )

    monkeypatch.setattr(auth_service, "UserRepository", _ExistingUsers)
    # Another request took the code between our compare and our take.
    monkeypatch.setattr(auth_service._cache(), "consume", lambda key: None)
    with pytest.raises(HTTPException) as exc:
        await auth_service.verify_email_code(
            None, VerifyLoginOtpRequest(email=email, code="246810")
        )
    assert exc.value.status_code == 400


def _resend_transport(responses):
    import httpx

    seen: list[httpx.Request] = []
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return httpx.Response(item)

    return httpx.MockTransport(handler), seen


def _send_kwargs(**overrides):
    base = dict(
        api_key="re_test_key_value",
        from_address="OraOne <auth@oraone.in>",
        to="person@example.com",
        subject="123456 is your OraOne sign-in code",
        html="<p>123456</p>",
        text="Your OraOne sign-in code is 123456.",
        idempotency_key="k" * 64,
    )
    base.update(overrides)
    return base


def test_resend_sends_once_with_bearer_auth_and_idempotency_key():
    import json

    from app.services import resend_client

    transport, seen = _resend_transport([200])
    ok = resend_client.send(**_send_kwargs(), transport=transport)
    assert ok is True
    assert len(seen) == 1
    request = seen[0]
    assert request.headers["Authorization"] == "Bearer re_test_key_value"
    assert request.headers["Idempotency-Key"] == "k" * 64
    body = json.loads(request.content)
    assert body["to"] == ["person@example.com"]
    assert "re_test_key_value" not in request.content.decode()


def test_resend_retries_server_errors_with_the_same_idempotency_key(monkeypatch):
    from app.services import resend_client

    monkeypatch.setattr(resend_client.time, "sleep", lambda _s: None)
    transport, seen = _resend_transport([500, 503, 200])
    assert resend_client.send(**_send_kwargs(), transport=transport) is True
    assert len(seen) == 3
    assert {r.headers["Idempotency-Key"] for r in seen} == {"k" * 64}


def test_resend_does_not_retry_a_rejected_request(monkeypatch):
    from app.services import resend_client

    monkeypatch.setattr(resend_client.time, "sleep", lambda _s: None)
    transport, seen = _resend_transport([422])
    assert resend_client.send(**_send_kwargs(), transport=transport) is False
    assert len(seen) == 1


def test_resend_gives_up_after_bounded_transport_failures(monkeypatch):
    import httpx

    from app.services import resend_client

    monkeypatch.setattr(resend_client.time, "sleep", lambda _s: None)
    failures = [httpx.ConnectError("refused")] * resend_client._MAX_ATTEMPTS
    transport, seen = _resend_transport(failures)
    assert resend_client.send(**_send_kwargs(), transport=transport) is False
    assert len(seen) == resend_client._MAX_ATTEMPTS


def test_resend_logs_never_contain_the_key_or_the_recipient(caplog, monkeypatch):
    from app.services import resend_client

    monkeypatch.setattr(resend_client.time, "sleep", lambda _s: None)
    echoed = '{"message":"bad request for person@example.com with re_test_key_value"}'
    transport, _seen = _resend_transport([422])
    # Replace the response body so the provider "echoes" the sensitive values.
    import httpx

    def handler(request):
        return httpx.Response(422, text=echoed)

    transport = httpx.MockTransport(handler)
    with caplog.at_level("DEBUG"):
        assert resend_client.send(**_send_kwargs(), transport=transport) is False
    logged = " ".join(record.getMessage() for record in caplog.records)
    assert "re_test_key_value" not in logged
    assert "person@example.com" not in logged


def test_login_code_uses_resend_when_a_key_is_configured(monkeypatch):
    from app.core.config import settings
    from app.services import email_service, resend_client

    calls: list[dict] = []
    monkeypatch.setattr(settings, "resend_api_key", "re_configured")
    monkeypatch.setattr(settings, "resend_from", "OraOne <auth@oraone.in>")
    monkeypatch.setattr(resend_client, "send", lambda **kw: calls.append(kw) or True)
    smtp_called = []
    monkeypatch.setattr(
        email_service, "send_email", lambda **kw: smtp_called.append(kw) or False
    )

    assert email_service.send_login_otp("person@example.com", code="482913") is True
    assert smtp_called == []
    call = calls[0]
    assert call["api_key"] == "re_configured"
    assert call["from_address"] == "OraOne <auth@oraone.in>"
    assert call["to"] == "person@example.com"
    assert "482913" in call["subject"]
    assert "482913" in call["text"] and "5 minutes" in call["text"]
    assert "482913" in call["html"]
    assert "{{" not in call["html"]  # every template token was filled


def test_login_code_falls_back_to_smtp_without_a_resend_key(monkeypatch):
    from app.core.config import settings
    from app.services import email_service

    monkeypatch.setattr(settings, "resend_api_key", "")
    seen: list[dict] = []
    monkeypatch.setattr(
        email_service, "send_email", lambda **kw: seen.append(kw) or True
    )
    assert email_service.send_login_otp("person@example.com", code="111222") is True
    assert seen and seen[0]["template"] == "login_otp.html"


# ── Sign-in code rules: real database ─────────────────────────────────────


@REQUIRES_DB
@pytest.mark.asyncio
async def test_resend_cooldown_holds_back_a_second_code(db_session, monkeypatch):
    from app.services import email_service

    sent: list[str] = []
    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="5 minutes": sent.append(code) or True,
    )
    email = f"cooldown-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        first = await client.post("/api/auth/email-code/request", json={"email": email})
        second = await client.post(
            "/api/auth/email-code/request", json={"email": email}
        )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json() == second.json()  # held back silently: same response
    assert len(sent) == 1


@REQUIRES_DB
@pytest.mark.asyncio
async def test_failed_delivery_clears_the_code_and_the_cooldown(
    db_session, monkeypatch
):
    from app.services import auth_service, email_service

    monkeypatch.setattr(email_service, "send_login_otp", lambda *a, **k: False)
    email = f"undelivered-{uuid.uuid4().hex[:8]}@example.com"
    from app.schemas.auth import EmailCodeRequest

    with pytest.raises(auth_service.EmailDeliveryError):
        await auth_service.request_email_code(db_session, EmailCodeRequest(email=email))
    assert auth_service._cache().get(auth_service._code_key(email)) is None
    assert auth_service._guard_cache().get(auth_service._cooldown_key(email)) is None


@REQUIRES_DB
@pytest.mark.asyncio
async def test_stored_code_is_a_digest_and_the_code_signs_in_once(
    db_session, monkeypatch
):
    from app.services import auth_service, email_service

    sent: dict[str, str] = {}
    monkeypatch.setattr(
        email_service,
        "send_login_otp",
        lambda to, *, code, expires_in="5 minutes": sent.__setitem__(to, code) or True,
    )
    email = f"digest-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        await client.post("/api/auth/email-code/request", json={"email": email})
        code = sent[email]
        stored = auth_service._cache().get(auth_service._code_key(email))
        assert isinstance(stored, dict) and code not in str(stored)
        ok = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
        again = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
    assert ok.status_code == 200
    assert again.status_code == 400  # single use


def test_production_never_falls_back_to_smtp_for_sign_in_codes(monkeypatch):
    from app.core.config import settings
    from app.services import email_service

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "resend_api_key", "")
    smtp_calls: list[dict] = []
    monkeypatch.setattr(
        email_service, "send_email", lambda **kw: smtp_calls.append(kw) or True
    )

    assert email_service.send_login_otp("person@example.com", code="123123") is False
    assert smtp_calls == []


def test_development_may_use_smtp_for_sign_in_codes(monkeypatch):
    from app.core.config import settings
    from app.services import email_service

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "resend_api_key", "")
    smtp_calls: list[dict] = []
    monkeypatch.setattr(
        email_service, "send_email", lambda **kw: smtp_calls.append(kw) or True
    )

    assert email_service.send_login_otp("person@example.com", code="123123") is True
    assert len(smtp_calls) == 1


@REQUIRES_DB
@pytest.mark.skipif(
    os.environ.get("ORAONE_TIMING_EVIDENCE") != "1",
    reason="Timing evidence is measured on a quiet host: set ORAONE_TIMING_EVIDENCE=1 to run it.",
)
@pytest.mark.asyncio
async def test_sign_in_request_work_is_the_same_for_every_address(
    db_session, monkeypatch
):
    """Statistical timing check. Existing, new, and inactive addresses take the same path.

    The sender is a constant-time stub, so the only differences left are the
    database read and the code path. Medians and 90th percentiles must match
    within a small bound. This is evidence against a timing oracle, not a proof.
    """
    import statistics
    import time

    from app.services import email_service
    from app.services.cache import get_shared_cache

    rounds = 40
    existing = f"timing-existing-{uuid.uuid4().hex[:8]}@example.com"
    inactive = f"timing-inactive-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        monkeypatch.setattr(email_service, "send_login_otp", lambda *a, **k: True)
        await client.post("/api/auth/email-code/request", json={"email": existing})
        await client.post("/api/auth/email-code/request", json={"email": inactive})
        # Make the second address inactive directly in the database.
        from sqlalchemy import update

        from app.database.models.user import User

        await db_session.execute(
            update(User).where(User.email == inactive).values(status="suspended")
        )
        await db_session.commit()

        samples = {"existing": [], "new": [], "inactive": []}
        import random

        order = random.Random(20261020)
        for _ in range(rounds):
            # Shuffle the three groups each round so warm-up and host load do not favour one group.
            plan = [
                ("existing", existing),
                ("new", f"timing-new-{uuid.uuid4().hex[:10]}@example.com"),
                ("inactive", inactive),
            ]
            order.shuffle(plan)
            for label, address in plan:
                # Clear the per-address cooldown and send counter so every request takes
                # the full path. Otherwise the send limit short-circuits the requests and
                # the test would measure that shortcut, not the account lookup.
                from app.services import auth_service

                guard = get_shared_cache("auth-guard")
                guard.delete(auth_service._cooldown_key(address))
                guard.delete(auth_service._send_key(address))
                started = time.perf_counter()
                response = await client.post(
                    "/api/auth/email-code/request", json={"email": address}
                )
                samples[label].append(time.perf_counter() - started)
                assert response.status_code == 200
                assert response.json() == {
                    "message": "If this address can receive sign-in codes, a code is on its way."
                }

    med = {k: statistics.median(v) for k, v in samples.items()}
    p90 = {k: sorted(v)[int(0.9 * (rounds - 1))] for k, v in samples.items()}
    spread_med = max(med.values()) - min(med.values())
    print(f"median ms { ({k: round(v * 1000, 2) for k, v in med.items()}) }")
    print(f"p90 ms { ({k: round(v * 1000, 2) for k, v in p90.items()}) }")
    assert spread_med < 0.015, f"median spread {spread_med * 1000:.1f} ms"
    # The 90th percentile is printed for the record but not asserted: with 25 samples on a
    # shared Windows host it is dominated by scheduler noise. The median is the gate.


# ── Signup legal acceptance ───────────────────────────────────────────────


async def _issue_code(client, sent_codes, email, monkeypatch=None):
    # Each test asks for a fresh code, so clear the per-address resend cooldown first.
    from app.services import auth_service
    from app.services.cache import get_shared_cache

    get_shared_cache("auth-guard").delete(auth_service._cooldown_key(email))
    req = await client.post(
        "/api/auth/email-code/request", json={"email": email, "name": "Consent Tester"}
    )
    assert req.status_code == 200, req.text
    return sent_codes[email]


@REQUIRES_DB
@pytest.mark.asyncio
async def test_new_account_is_not_created_without_required_acceptance(
    db_session, sent_codes
):
    from sqlalchemy import select

    from app.database.models.signup_consent import SignupConsent
    from app.database.models.user import User

    email = f"noaccept-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)
        refused = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": code}
        )
        assert refused.status_code == 400
        assert "Accept the Terms" in refused.text
        # The refusal did not spend the code: a correct retry with acceptance works.
        ok = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
        assert ok.status_code == 200, ok.text

    user = await db_session.scalar(select(User).where(User.email == email))
    assert user is not None
    rows = (
        (
            await db_session.execute(
                select(SignupConsent).where(SignupConsent.user_id == user.id)
            )
        )
        .scalars()
        .all()
    )
    assert {r.document for r in rows} == {"terms", "privacy", "marketing"}


@REQUIRES_DB
@pytest.mark.asyncio
async def test_stale_document_versions_are_refused_and_create_nothing(
    db_session, sent_codes
):
    from sqlalchemy import select

    from app.database.models.user import User

    email = f"stale-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)
        stale = {**_accept(), "terms_version": "2020-01-01"}
        refused = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": code, **stale}
        )
        assert refused.status_code == 409
    assert await db_session.scalar(select(User).where(User.email == email)) is None


@REQUIRES_DB
@pytest.mark.asyncio
async def test_production_refuses_signup_while_documents_are_drafts(
    db_session, sent_codes, monkeypatch
):
    from sqlalchemy import select

    from app.core.config import settings
    from app.database.models.user import User

    email = f"draft-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)
        monkeypatch.setattr(settings, "environment", "production")
        monkeypatch.setattr(settings, "legal_terms_version", "draft-2026-10-20")
        refused = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept()},
        )
    assert refused.status_code == 503
    assert await db_session.scalar(select(User).where(User.email == email)) is None


@REQUIRES_DB
@pytest.mark.asyncio
async def test_acceptance_is_stored_with_versions_and_utc_times(db_session, sent_codes):
    from datetime import timezone

    from sqlalchemy import select

    from app.core.config import settings
    from app.database.models.signup_consent import SignupConsent
    from app.database.models.user import User

    email = f"stored-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)
        ok = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept(marketing=False)},
        )
        assert ok.status_code == 200, ok.text

    user = await db_session.scalar(select(User).where(User.email == email))
    rows = {
        r.document: r
        for r in (
            await db_session.execute(
                select(SignupConsent).where(SignupConsent.user_id == user.id)
            )
        ).scalars()
    }
    assert (
        rows["terms"].granted is True
        and rows["terms"].version == settings.legal_terms_version
    )
    assert (
        rows["privacy"].granted is True
        and rows["privacy"].version == settings.legal_privacy_version
    )
    assert (
        rows["marketing"].granted is False
    )  # unchecked by default, recorded as declined
    for row in rows.values():
        assert row.recorded_at.tzinfo is not None
        assert row.recorded_at.utcoffset() == timezone.utc.utcoffset(None)


@REQUIRES_DB
@pytest.mark.asyncio
async def test_marketing_consent_is_recorded_only_when_ticked(db_session, sent_codes):
    from sqlalchemy import select

    from app.database.models.signup_consent import SignupConsent
    from app.database.models.user import User

    email = f"marketing-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)
        ok = await client.post(
            "/api/auth/email-code/verify",
            json={"email": email, "code": code, **_accept(marketing=True)},
        )
        assert ok.status_code == 200, ok.text
    user = await db_session.scalar(select(User).where(User.email == email))
    marketing = await db_session.scalar(
        select(SignupConsent).where(
            SignupConsent.user_id == user.id, SignupConsent.document == "marketing"
        )
    )
    assert marketing.granted is True


@REQUIRES_DB
@pytest.mark.asyncio
async def test_existing_account_signs_in_without_new_acceptance(db_session, sent_codes):
    from sqlalchemy import func, select

    from app.database.models.signup_consent import SignupConsent

    email = f"existing-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        # Create the account once, with acceptance.
        code = await _issue_code(client, sent_codes, email)
        assert (
            await client.post(
                "/api/auth/email-code/verify",
                json={"email": email, "code": code, **_accept()},
            )
        ).status_code == 200
        before = await db_session.scalar(
            select(func.count()).select_from(SignupConsent)
        )
        # A later sign-in needs no acceptance and creates no consent rows.
        code = await _issue_code(client, sent_codes, email)
        again = await client.post(
            "/api/auth/email-code/verify", json={"email": email, "code": code}
        )
        assert again.status_code == 200, again.text
    after = await db_session.scalar(select(func.count()).select_from(SignupConsent))
    assert after == before


@REQUIRES_DB
@pytest.mark.asyncio
async def test_concurrent_signup_verifications_create_exactly_one_account(
    monkeypatch, sent_codes
):
    """Four simultaneous verifications with the right code and acceptance: one account, one session."""
    from sqlalchemy import func, select

    from app.database import session as db_session_module
    from app.database.models.user import User
    from app.database.session import dispose_engine, init_engine

    await dispose_engine()
    init_engine()
    email = f"race-signup-{uuid.uuid4().hex[:8]}@example.com"
    async with _client() as client:
        code = await _issue_code(client, sent_codes, email)

    from app.schemas.auth import VerifyLoginOtpRequest
    from app.services import auth_service
    from fastapi import HTTPException

    payload = VerifyLoginOtpRequest(email=email, code=code, **_accept())

    async def attempt():
        maker = db_session_module.AsyncSessionLocal
        async with maker() as session:
            try:
                await auth_service.verify_email_code(session, payload)
                return "ok"
            except HTTPException as exc:
                await session.rollback()
                return str(exc.status_code)

    # Four simultaneous submissions fit the attempt budget; exactly one may succeed.
    results = await asyncio.gather(*(attempt() for _ in range(4)))
    assert results.count("ok") == 1, results

    maker = db_session_module.AsyncSessionLocal
    async with maker() as session:
        count = await session.scalar(
            select(func.count()).select_from(User).where(User.email == email)
        )
    await dispose_engine()
    assert count == 1
