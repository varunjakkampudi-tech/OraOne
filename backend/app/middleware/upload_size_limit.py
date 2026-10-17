"""Reject oversized upload requests from their Content-Length before parsing.

Pure ASGI so the body is never touched: a request that declares more bytes than
the route allows gets a 413 immediately. Requests without a declared length are
bounded by ``read_capped`` in the route itself.
"""

from __future__ import annotations

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

#: Path -> maximum declared request body in bytes (file plus multipart overhead).
MB = 1024 * 1024
DEFAULT_UPLOAD_LIMITS: dict[str, int] = {
    "/api/documents/upload": 26 * MB,
    "/api/branding/logo": 3 * MB,
    "/api/branding/icon": 3 * MB,
}


class UploadSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, limits: dict[str, int] | None = None) -> None:
        self.app = app
        self.limits = dict(DEFAULT_UPLOAD_LIMITS if limits is None else limits)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") != "POST":
            await self.app(scope, receive, send)
            return
        limit = self.limits.get(scope.get("path", ""))
        if limit is None:
            await self.app(scope, receive, send)
            return
        declared = None
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
                break
        if declared is not None and declared > limit:
            response = JSONResponse(
                {"detail": "Upload is larger than this endpoint allows."},
                status_code=413,
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
