"""Startup configuration checks: production-like environments fail closed."""

from __future__ import annotations

import pytest

from app.core.startup_checks import (
    StartupConfigurationError,
    find_configuration_problems,
    is_production_like,
    validate_startup_configuration,
)

JWT = "j" * 48
SECRET_VALUES = ["sid-secret-value", "token-secret-value", "app-secret-value"]


def base_env(environment: str = "production", **extra: str) -> dict[str, str]:
    env = {
        "ENVIRONMENT": environment,
        "JWT_SECRET_KEY": JWT,
        "OPENROUTER_API_KEY": "or-key-placeholder",
    }
    env.update(extra)
    return env


PROD_LIKE = ["production", "prod", "staging"]


@pytest.mark.parametrize("environment", PROD_LIKE)
def test_complete_production_config_starts(environment):
    env = base_env(environment)
    validate_startup_configuration(env)  # no raise
    assert find_configuration_problems(env) == []


@pytest.mark.parametrize("environment", ["development", "dev", "test", ""])
def test_development_never_blocks_startup(environment):
    env = {"ENVIRONMENT": environment}
    validate_startup_configuration(env)  # no raise even with nothing configured


def test_development_with_partial_twilio_is_not_blocked():
    env = {"ENVIRONMENT": "development", "TWILIO_ACCOUNT_SID": "AC-placeholder"}
    validate_startup_configuration(env)


def test_environment_detection_is_case_and_space_insensitive():
    assert is_production_like({"ENVIRONMENT": "  Production "})
    assert not is_production_like({"ENVIRONMENT": "development"})
    assert not is_production_like({})


@pytest.mark.parametrize("environment", PROD_LIKE)
def test_missing_jwt_secret_is_refused(environment):
    env = base_env(environment)
    del env["JWT_SECRET_KEY"]
    with pytest.raises(StartupConfigurationError) as exc:
        validate_startup_configuration(env)
    assert "JWT_SECRET_KEY" in str(exc.value)


def test_short_jwt_secret_is_refused():
    env = base_env("production", JWT_SECRET_KEY="short")
    with pytest.raises(StartupConfigurationError, match="JWT_SECRET_KEY"):
        validate_startup_configuration(env)


def test_twilio_partly_set_requires_account_sid_and_token():
    env = base_env(
        "production",
        TWILIO_AUTH_TOKEN="token-secret-value",
        PUBLIC_API_BASE_URL="https://api.example.com",
    )
    problems = find_configuration_problems(env)
    assert problems == ["TWILIO_ACCOUNT_SID"]


def test_twilio_phone_number_alone_counts_as_configured():
    env = base_env("production", TWILIO_PHONE_NUMBER="+15550000000")
    problems = find_configuration_problems(env)
    assert any(p.startswith("TWILIO_ACCOUNT_SID") for p in problems)
    assert any(p.startswith("TWILIO_AUTH_TOKEN") for p in problems)
    assert any(p.startswith("PUBLIC_API_BASE_URL") for p in problems)


def test_twilio_fully_set_with_https_base_url_passes():
    env = base_env(
        "production",
        TWILIO_ACCOUNT_SID="sid-secret-value",
        TWILIO_AUTH_TOKEN="token-secret-value",
        PUBLIC_API_BASE_URL="https://api.example.com",
    )
    assert find_configuration_problems(env) == []


def test_twilio_requires_public_base_url():
    env = base_env(
        "production",
        TWILIO_ACCOUNT_SID="sid-secret-value",
        TWILIO_AUTH_TOKEN="token-secret-value",
    )
    problems = find_configuration_problems(env)
    assert problems == ["PUBLIC_API_BASE_URL (required when Twilio is configured)"]


def test_twilio_public_base_url_must_be_https():
    env = base_env(
        "production",
        TWILIO_ACCOUNT_SID="sid-secret-value",
        TWILIO_AUTH_TOKEN="token-secret-value",
        PUBLIC_API_BASE_URL="http://api.example.com",
    )
    problems = find_configuration_problems(env)
    assert len(problems) == 1
    assert problems[0].startswith("PUBLIC_API_BASE_URL")
    assert "https" in problems[0]


def test_twilio_not_configured_does_not_require_public_base_url():
    env = base_env("production")
    assert find_configuration_problems(env) == []


@pytest.mark.parametrize(
    "token_name", ["META_WHATSAPP_ACCESS_TOKEN", "META_INSTAGRAM_ACCESS_TOKEN"]
)
def test_meta_access_token_requires_app_secret(token_name):
    env = base_env("production", **{token_name: "meta-token-placeholder"})
    problems = find_configuration_problems(env)
    assert len(problems) == 1
    assert problems[0].startswith("META_WHATSAPP_APP_SECRET")


def test_meta_app_secret_satisfies_whatsapp_and_instagram():
    env = base_env(
        "production",
        META_WHATSAPP_ACCESS_TOKEN="meta-token-placeholder",
        META_INSTAGRAM_ACCESS_TOKEN="ig-token-placeholder",
        META_WHATSAPP_APP_SECRET="app-secret-value",
    )
    assert find_configuration_problems(env) == []


def test_meta_app_secret_not_required_without_meta_tokens():
    env = base_env("production")
    assert find_configuration_problems(env) == []


def test_missing_openrouter_key_is_refused():
    env = base_env("production")
    del env["OPENROUTER_API_KEY"]
    problems = find_configuration_problems(env)
    assert problems == ["OPENROUTER_API_KEY (required for AI replies)"]


def test_blank_values_count_as_missing():
    env = base_env("production", OPENROUTER_API_KEY="   ")
    assert any(
        p.startswith("OPENROUTER_API_KEY") for p in find_configuration_problems(env)
    )


def test_error_lists_names_but_never_values():
    env = base_env(
        "production",
        TWILIO_AUTH_TOKEN="token-secret-value",
        PUBLIC_API_BASE_URL="http://api.example.com",
        META_INSTAGRAM_ACCESS_TOKEN="ig-token-placeholder",
    )
    env.pop("OPENROUTER_API_KEY")
    with pytest.raises(StartupConfigurationError) as exc:
        validate_startup_configuration(env)
    message = str(exc.value)
    assert "TWILIO_ACCOUNT_SID" in message
    assert "PUBLIC_API_BASE_URL" in message
    assert "META_WHATSAPP_APP_SECRET" in message
    assert "OPENROUTER_API_KEY" in message
    for secret in [
        "token-secret-value",
        "ig-token-placeholder",
        "http://api.example.com",
    ]:
        assert secret not in message


def test_default_path_reads_process_environment(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("JWT_SECRET_KEY", JWT)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWILIO_PHONE_NUMBER", raising=False)
    with pytest.raises(StartupConfigurationError, match="OPENROUTER_API_KEY"):
        validate_startup_configuration()


def test_default_path_development_process_environment_is_not_blocked(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    validate_startup_configuration()
