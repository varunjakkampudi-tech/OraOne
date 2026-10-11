"""Request/response models for the auth API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SignUpRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8, max_length=256)


class ConfirmSignUpRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class ResendConfirmationRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class VerifyLoginOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class LoginOtpRequiredResponse(BaseModel):
    otp_required: bool = True
    email: EmailStr
    message: str = "A verification code was sent to your email."


class RefreshTokenRequest(BaseModel):
    # Optional — a browser session may rely solely on the httpOnly refresh
    # cookie instead (see app/api/auth/routes.py::refresh).
    refresh_token: Optional[str] = Field(default=None, min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=256)


class ConfirmForgotPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")
    new_password: str = Field(..., min_length=8, max_length=256)


class TokensResponse(BaseModel):
    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int


class UserProfile(BaseModel):
    userId: str
    email: EmailStr
    name: str
    role: str = "user"
    plan: str = "free"
    status: str = "active"
    createdAt: Optional[datetime] = None
    lastLogin: Optional[datetime] = None


class MessageResponse(BaseModel):
    message: str


# ──────────────────────────────────────────────────────────────────
# Phase 3 — Postgres identity payload (user + org + membership)
# ──────────────────────────────────────────────────────────────────

class IdentityUser(BaseModel):
    id: str
    cognito_sub: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class IdentityOrganization(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    owner_user_id: str
    created_at: datetime


class IdentityMembership(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: str
    status: str
    joined_at: Optional[datetime] = None


class IdentityResponse(BaseModel):
    """Returned by GET /api/auth/identity — created on first call, reused after."""

    user: IdentityUser
    organization: IdentityOrganization
    membership: IdentityMembership
    is_new_user: bool
