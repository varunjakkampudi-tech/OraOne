"""Admin log viewer: recent server errors, per-request lookup, audited downloads."""

from app.api.admin_logs.routes import router

__all__ = ["router"]
