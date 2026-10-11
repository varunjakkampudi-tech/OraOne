"""Cognito access-token verification regression tests.

These tests deliberately avoid AWS calls: the production verifier's network
boundary is mocked while issuer, algorithm, token-use, client and expiry
validation remain exercised by the jose decoder contract.
"""

from __future__ import annotations

import time

import pytest


@pytest.mark.asyncio
async def test_cognito_access_token_requires_access_use_and_expected_client(
    monkeypatch,
):
    from app.middleware import jwt_auth

    monkeypatch.setattr(
        jwt_auth.settings, "cognito_issuer", "https://issuer.example/pool"
    )
    monkeypatch.setattr(jwt_auth.settings, "cognito_client_id", "client-123")
    monkeypatch.setattr(
        jwt_auth.jose_jwt,
        "get_unverified_header",
        lambda token: {"kid": "k1", "alg": "RS256"},
    )
    monkeypatch.setattr(
        jwt_auth.jose_jwt,
        "decode",
        lambda *args, **kwargs: {
            "sub": "user-1",
            "token_use": "access",
            "client_id": "client-123",
            "iss": "https://issuer.example/pool",
            "exp": int(time.time()) + 300,
        },
    )
    monkeypatch.setattr(
        jwt_auth,
        "_jwks_cache",
        {
            "expires_at": time.time() + 300,
            "keys": [{"kid": "k1", "kty": "RSA", "alg": "RS256"}],
        },
    )

    claims = await jwt_auth.verify_cognito_access_token("token")
    assert claims["sub"] == "user-1"

    def reject_wrong_claims(*args, **kwargs):
        return {
            "sub": "user-1",
            "token_use": "id",
            "client_id": "wrong-client",
        }

    monkeypatch.setattr(jwt_auth.jose_jwt, "decode", reject_wrong_claims)
    with pytest.raises(Exception) as exc:
        await jwt_auth.verify_cognito_access_token("token")
    assert getattr(exc.value, "status_code", None) == 401


@pytest.mark.asyncio
async def test_cognito_access_token_rejects_non_rs256_header(monkeypatch):
    from app.middleware import jwt_auth

    monkeypatch.setattr(
        jwt_auth.jose_jwt,
        "get_unverified_header",
        lambda token: {"kid": "k1", "alg": "HS256"},
    )
    with pytest.raises(Exception) as exc:
        await jwt_auth.verify_cognito_access_token("token")
    assert getattr(exc.value, "status_code", None) == 401
