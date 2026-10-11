"""Channel adapters package — provider glue for the omnichannel pipeline."""
from app.services.channels.adapters import (
    ChannelAdapter,
    ParsedInbound,
    get_adapter,
    register,
    supported_providers,
)

__all__ = [
    "ChannelAdapter",
    "ParsedInbound",
    "get_adapter",
    "register",
    "supported_providers",
]
