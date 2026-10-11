"""Pydantic schemas for the RBAC API (Phase 12, Module 4)."""

from __future__ import annotations

from typing import Dict, List

from pydantic import Field

from pydantic import BaseModel


class MyPermissionsResponse(BaseModel):
    role: str
    platform_role: str = "user"
    permissions: List[str]


class RoleMatrixResponse(BaseModel):
    permissions: List[str]
    roles: Dict[str, List[str]]


class PlatformRoleUpdateRequest(BaseModel):
    role: str = Field(min_length=1, max_length=32)


class PlatformUserRoleResponse(BaseModel):
    user_id: str
    cognito_sub: str
    email: str
    platform_role: str
