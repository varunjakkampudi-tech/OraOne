"""Pydantic schemas for the RBAC API (Phase 12, Module 4)."""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel


class MyPermissionsResponse(BaseModel):
    role: str
    permissions: List[str]


class RoleMatrixResponse(BaseModel):
    permissions: List[str]
    roles: Dict[str, List[str]]
