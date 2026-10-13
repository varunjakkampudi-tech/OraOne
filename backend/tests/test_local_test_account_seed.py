"""Safety contract for the optional local QA account seeder.

These tests do not create accounts, touch a database or bypass the real OTP flow.
"""

import pytest

from scripts.seed_local_test_account import validate_local_environment


@pytest.fixture
def local_seed_env(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("AUTH_PROVIDER", "self_hosted")
    monkeypatch.setenv("ORAONE_LOCAL_TEST_ACK", "I_UNDERSTAND_THIS_IS_LOCAL_ONLY")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://tester:secret@127.0.0.1:5433/oraone")
    monkeypatch.setenv("ORAONE_LOCAL_TEST_PASSWORD", "test@oraone.in")


def test_local_seed_allows_explicit_opt_in(local_seed_env):
    assert validate_local_environment() == "test@oraone.in"


@pytest.mark.parametrize("environment", ["production", "prod", "staging", "", "test"])
def test_local_seed_rejects_non_development(local_seed_env, monkeypatch, environment):
    monkeypatch.setenv("ENVIRONMENT", environment)
    with pytest.raises(RuntimeError, match="ENVIRONMENT=development"):
        validate_local_environment()


def test_local_seed_rejects_other_identity_provider(local_seed_env, monkeypatch):
    monkeypatch.setenv("AUTH_PROVIDER", "cognito")
    with pytest.raises(RuntimeError, match="AUTH_PROVIDER=self_hosted"):
        validate_local_environment()


def test_local_seed_rejects_missing_acknowledgement(local_seed_env, monkeypatch):
    monkeypatch.delenv("ORAONE_LOCAL_TEST_ACK")
    with pytest.raises(RuntimeError, match="ORAONE_LOCAL_TEST_ACK"):
        validate_local_environment()


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+asyncpg://tester:secret@db.internal:5432/oraone",
        "postgresql+asyncpg://tester:secret@postgres:5432/oraone",
        "postgresql+asyncpg://tester:secret@203.0.113.1:5432/oraone",
    ],
)
def test_local_seed_rejects_remote_or_container_db(local_seed_env, monkeypatch, url):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(RuntimeError, match="database host"):
        validate_local_environment()


def test_local_seed_rejects_missing_password(local_seed_env, monkeypatch):
    monkeypatch.delenv("ORAONE_LOCAL_TEST_PASSWORD")
    with pytest.raises(RuntimeError, match="ORAONE_LOCAL_TEST_PASSWORD"):
        validate_local_environment()


def test_local_seed_rejects_short_password(local_seed_env, monkeypatch):
    monkeypatch.setenv("ORAONE_LOCAL_TEST_PASSWORD", "password")
    with pytest.raises(RuntimeError, match="at least 12"):
        validate_local_environment()


def test_local_seed_supports_explicit_loopback_db_host(local_seed_env, monkeypatch):
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.setenv("DB_HOST", "localhost")
    assert validate_local_environment() == "test@oraone.in"
