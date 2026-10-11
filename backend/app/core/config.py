"""Centralized runtime configuration.

Authentication supports a deliberately explicit migration boundary:
``self_hosted`` is available for local development and staged migration;
``cognito`` verifies AWS Cognito access tokens against the user-pool JWKS.
Production Compose must select and fully configure the intended provider.

Fail-fast policy: required values raise at import time if missing. This
prevents silently booting with a weak/default JWT secret in production.
"""
import os
from pathlib import Path

from dotenv import load_dotenv


# Always load backend/.env regardless of current working directory.
# Explicit process/container environment wins over the local convenience file.
# This is required for Compose/Hostinger secret injection and safe overrides.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_ROOT / ".env", override=False)


def _required(key: str, *aliases: str) -> str:
    """Return the value of `key` (or first matching alias), else raise."""
    for k in (key, *aliases):
        value = os.environ.get(k)
        if value:
            return value
    aliases_str = f" (aliases: {', '.join(aliases)})" if aliases else ""
    raise RuntimeError(
        f"Missing required environment variable: {key}{aliases_str}. "
        f"Set it in backend/.env before starting the server."
    )


class Settings:
    #: Optional — only consulted as a region fallback for the Bedrock
    #: embeddings provider and S3/SES if those are configured.
    aws_region: str = os.environ.get("AWS_REGION", "us-east-1")

    # ---- Identity provider ----
    auth_provider: str = os.environ.get("AUTH_PROVIDER", "self_hosted").strip().lower()
    cognito_user_pool_id: str = os.environ.get("COGNITO_USER_POOL_ID", "").strip()
    cognito_region: str = os.environ.get("COGNITO_REGION", os.environ.get("AWS_REGION", "")).strip()
    cognito_client_id: str = os.environ.get("COGNITO_CLIENT_ID", "").strip()
    cognito_issuer: str = os.environ.get("COGNITO_ISSUER", "").strip()

    # ---- Self-hosted migration auth ----
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", os.environ.get("LOCAL_AUTH_SECRET", ""))
    jwt_access_ttl_minutes: int = int(os.environ.get("JWT_ACCESS_TTL_MINUTES", "15"))
    jwt_refresh_ttl_days: int = int(os.environ.get("JWT_REFRESH_TTL_DAYS", "30"))
    jwt_leeway_seconds: int = int(os.environ.get("JWT_LEEWAY_SECONDS", "60"))
    jwt_issuer_name: str = os.environ.get("JWT_ISSUER", "oraone-api")

    def __init__(self) -> None:
        if self.auth_provider not in {"self_hosted", "cognito"}:
            raise RuntimeError("AUTH_PROVIDER must be either 'self_hosted' or 'cognito'.")
        if self.auth_provider == "self_hosted" and len(self.jwt_secret_key) < 32:
            raise RuntimeError(
                "JWT_SECRET_KEY must be at least 32 characters. Generate one with: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if self.auth_provider == "cognito":
            missing = [
                name for name, value in {
                    "COGNITO_USER_POOL_ID": self.cognito_user_pool_id,
                    "COGNITO_REGION": self.cognito_region,
                    "COGNITO_CLIENT_ID": self.cognito_client_id,
                }.items() if not value
            ]
            if missing:
                raise RuntimeError(
                    "Cognito auth requires: " + ", ".join(missing)
                )

    @property
    def jwt_issuer(self) -> str:
        return self.jwt_issuer_name

    @property
    def cognito_jwks_url(self) -> str:
        issuer = self.cognito_issuer or (
            f"https://cognito-idp.{self.cognito_region}.amazonaws.com/"
            f"{self.cognito_user_pool_id}"
        )
        return f"{issuer.rstrip('/')}/.well-known/jwks.json"

    @property
    def cognito_token_issuer(self) -> str:
        return self.cognito_issuer or self.cognito_jwks_url.removesuffix("/.well-known/jwks.json")


settings = Settings()
