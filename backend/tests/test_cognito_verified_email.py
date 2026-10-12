"""Regression coverage for Cognito's documented UserInfo string booleans."""

import pytest

from app.api.auth.routes import _verified_cognito_email


@pytest.mark.parametrize("verified", [True, "true"])
def test_cognito_accepts_positive_verification(verified):
    assert (
        _verified_cognito_email(
            {"email": "verified@example.com", "email_verified": verified}
        )
        == "verified@example.com"
    )


@pytest.mark.parametrize("verified", [False, "false", None, "", "TRUE", 1, "1"])
def test_cognito_rejects_unverified_or_truthy_values(verified):
    assert (
        _verified_cognito_email(
            {"email": "unverified@example.com", "email_verified": verified}
        )
        is None
    )


@pytest.mark.parametrize("email", [None, "", "   ", 123])
def test_cognito_requires_email_string(email):
    assert _verified_cognito_email({"email": email, "email_verified": "true"}) is None


@pytest.mark.asyncio
async def test_identity_rejects_userinfo_subject_mismatch(monkeypatch):
    from fastapi import HTTPException
    from app.api.auth import routes

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "sub": "different-user",
                "email": "verified@example.com",
                "email_verified": "true",
            }

    class Client:
        def __init__(self, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(routes.settings, "auth_provider", "cognito")
    monkeypatch.setattr(routes.httpx, "AsyncClient", Client)
    with pytest.raises(HTTPException) as error:
        await routes.identity(
            claims={"sub": "validated-user"}, access_token="test-only", session=None
        )
    assert error.value.status_code == 401
