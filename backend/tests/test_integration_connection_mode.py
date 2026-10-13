import pytest
from fastapi import HTTPException

from app.api.integrations.routes import _connection_mode
from app.database.models.integration import ConnectionType


@pytest.mark.parametrize("environment", ["development", "dev", "test", "testing"])
def test_mock_connection_requires_explicit_request_in_nonproduction(environment):
    assert (
        _connection_mode(
            mock_requested=True,
            real_oauth_ready=False,
            environment=environment,
        )
        == ConnectionType.mock
    )


def test_unconfigured_integration_fails_closed_for_normal_user_connect():
    with pytest.raises(HTTPException) as exc_info:
        _connection_mode(
            mock_requested=False,
            real_oauth_ready=False,
            environment="development",
        )

    assert exc_info.value.status_code == 503


@pytest.mark.parametrize("environment", ["production", "prod", "staging"])
def test_mock_connection_is_rejected_outside_local_test_environments(environment):
    with pytest.raises(HTTPException) as exc_info:
        _connection_mode(
            mock_requested=True,
            real_oauth_ready=False,
            environment=environment,
        )

    assert exc_info.value.status_code == 503


def test_configured_oauth_uses_real_connection_without_mock_flag():
    assert (
        _connection_mode(
            mock_requested=False,
            real_oauth_ready=True,
            environment="production",
        )
        == ConnectionType.oauth
    )
