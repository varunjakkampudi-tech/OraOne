"""Centralized runtime configuration.

Authentication is self-hosted: users sign in with a one-time email code and
the API issues short-lived JWT access tokens plus a refresh token. Settings
are read once at import time and validated immediately, so a misconfigured
deployment fails at start-up instead of at the first request.

Fail-fast policy: required values raise at import time when missing or weak.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Always load backend/.env regardless of the working directory. Variables that
# are already set in the process environment take precedence over the file.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_BACKEND_ROOT / ".env", override=False)

# Values saved from the admin configuration console take effect at start-up,
# before the settings below are read. Failures never block start-up.
from app.core.config_overrides import (  # noqa: E402
    apply_stored_overrides_at_startup,
)

apply_stored_overrides_at_startup()

_PRODUCTION_ENVIRONMENTS = {"production", "prod", "staging"}
_MIN_JWT_SECRET_LENGTH = 32


class Settings:
    """Typed view over environment variables used by the backend."""

    # Unset ENVIRONMENT is treated as production (fail closed). Local work must
    # set ENVIRONMENT=development explicitly to enable development-only paths.
    environment: str = os.environ.get("ENVIRONMENT", "").strip().lower() or "production"

    # Self-hosted authentication: Argon2 password hashes and HS256 JWTs.
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "")
    jwt_access_ttl_minutes: int = int(os.environ.get("JWT_ACCESS_TTL_MINUTES", "15"))
    jwt_refresh_ttl_days: int = int(os.environ.get("JWT_REFRESH_TTL_DAYS", "30"))
    jwt_leeway_seconds: int = int(os.environ.get("JWT_LEEWAY_SECONDS", "60"))
    jwt_issuer_name: str = os.environ.get("JWT_ISSUER", "oraone-api")

    def __init__(self) -> None:
        """Validate the security-critical settings before the app starts."""
        if len(self.jwt_secret_key) < _MIN_JWT_SECRET_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET_KEY must be at least {_MIN_JWT_SECRET_LENGTH} characters. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )

    @property
    def is_production(self) -> bool:
        """True for production-like deployments, where dev shortcuts are forbidden."""
        return self.environment in _PRODUCTION_ENVIRONMENTS

    @property
    def jwt_issuer(self) -> str:
        """The ``iss`` claim written into and required on every access token."""
        return self.jwt_issuer_name


settings = Settings()
