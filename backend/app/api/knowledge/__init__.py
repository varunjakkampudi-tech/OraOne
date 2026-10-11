"""Knowledge API package (Phase 6 — Knowledge Base Foundation)."""
from app.api.knowledge.routes import router
from app.api.knowledge.organization import router as knowledge_org_router
from app.api.knowledge.sources import router as knowledge_sources_router

__all__ = ["router", "knowledge_org_router", "knowledge_sources_router"]
