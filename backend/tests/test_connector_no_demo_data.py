"""Application connectors must never manufacture external-provider content."""

import pytest

from app.connectors.base import BaseConnector, NotConnectedError


@pytest.mark.parametrize(
    "operation", ["connect", "refresh_token", "sync", "browse", "search", "list"]
)
def test_unimplemented_connector_fails_instead_of_returning_demo_data(operation):
    connector = BaseConnector()
    with pytest.raises(NotConnectedError):
        getattr(connector, operation)("query") if operation == "search" else getattr(
            connector, operation
        )()


def test_unimplemented_connector_does_not_claim_health():
    assert BaseConnector().health() is False
