"""Log-safe request labels.

Raw request paths can carry credentials: the Telegram webhook is
``/api/omnichannel/telegram/{bot_token}/inbound`` and public share links carry
their token in the path. Logs must therefore record the matched route
*template* (``/api/chat/share/{token}``), never the concrete path, and fall
back to a fixed label when no route matches.
"""

from __future__ import annotations

from typing import Any, Mapping

UNMATCHED_ROUTE = "unmatched"


def route_template(scope: Mapping[str, Any]) -> str:
    """Return the matched route template for an ASGI ``scope``.

    FastAPI stores the matched route on the scope during routing, and routing
    finishes before any dependency or handler runs, so the template is available
    to the access log and to auth/context log lines. Requests that matched no
    route (404s, or failures before routing) get ``UNMATCHED_ROUTE``.
    """
    template = getattr(scope.get("route"), "path", None)
    if isinstance(template, str) and template:
        return template
    return UNMATCHED_ROUTE


def request_route_label(request: Any) -> str:
    """Convenience wrapper: the log-safe route label for a Starlette request."""
    return route_template(request.scope)
