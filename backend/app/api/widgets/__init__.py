"""Embedded Website Widget API package (R6).

Exposes two routers:
* ``router``        — admin CRUD/config/analytics (org-scoped, authenticated)
* ``public_router`` — the loader config + visitor chat endpoints
                      (unauthenticated, domain-restricted)
"""
from app.api.widgets.routes import router
from app.api.widgets.public import public_router

__all__ = ["router", "public_router"]
