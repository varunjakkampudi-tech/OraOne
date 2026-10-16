"""Request and response models for the authentication API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

#: Length of the one-time sign-in code emailed to the user.
SIGN_IN_CODE_PATTERN = r"^\d{6}$"


class EmailCodeRequest(BaseModel):
    """Start a passwordless sign-in by emailing a one-time code."""

    email: EmailStr
    # Used only when the address is new and an account is created from this request.
    name: Optional[str] = Field(default=None, max_length=120)


class VerifyLoginOtpRequest(BaseModel):
    """Exchange an emailed one-time code for a session."""

    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=SIGN_IN_CODE_PATTERN)


class LoginRequest(BaseModel):
    """Development-only password sign-in (see ``ALLOW_DEV_PASSWORD_LOGIN``)."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=256)


class RefreshTokenRequest(BaseModel):
    """Refresh-token body. A browser session may rely on the httpOnly cookie instead."""

    refresh_token: Optional[str] = Field(default=None, min_length=1)


class UpdateProfileRequest(BaseModel):
    """Change the signed-in user's display name."""

    full_name: str = Field(..., min_length=1, max_length=120)


class TokensResponse(BaseModel):
    """Access and refresh tokens issued after a successful sign-in or refresh."""

    access_token: str
    id_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int


class UserProfile(BaseModel):
    """Public profile of the signed-in user."""

    userId: str
    email: EmailStr
    name: str
    role: str = "user"
    platform_role: str = "user"
    plan: str = "free"
    status: str = "active"
    createdAt: Optional[datetime] = None
    lastLogin: Optional[datetime] = None


class MessageResponse(BaseModel):
    """A short human-readable confirmation."""

    message: str


class IdentityUser(BaseModel):
    """User record inside the identity payload."""

    id: str
    auth_subject: str
    email: EmailStr
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str
    platform_role: str
    status: str
    created_at: datetime
    last_login_at: Optional[datetime] = None


class IdentityOrganization(BaseModel):
    """Organization record inside the identity payload."""

    id: str
    name: str
    slug: str
    plan: str
    owner_user_id: str
    created_at: datetime


class IdentityMembership(BaseModel):
    """Membership record inside the identity payload."""

    id: str
    organization_id: str
    user_id: str
    role: str
    status: str
    joined_at: Optional[datetime] = None


class IdentityResponse(BaseModel):
    """Returned by ``GET /api/auth/identity``: created on the first call, reused after."""

    user: IdentityUser
    organization: IdentityOrganization
    membership: IdentityMembership
    is_new_user: bool
