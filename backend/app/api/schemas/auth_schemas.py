"""Pydantic V2 request/response models for auth endpoints.

Every endpoint validates its input via a Pydantic model — no raw dict
request bodies.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ── Request Models ────────────────────────────────────


class SignupRequest(BaseModel):
    """POST /api/auth/signup body."""

    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Minimum 8 characters",
    )
    full_name: Optional[str] = Field(
        None,
        max_length=100,
        description="Optional display name",
    )


class LoginRequest(BaseModel):
    """POST /api/auth/login body."""

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=72)


class ProfileUpdateRequest(BaseModel):
    """PATCH /api/auth/profile body.

    All fields are optional — only provided fields are updated.
    """

    full_name: Optional[str] = Field(None, max_length=100)
    channel_id: Optional[str] = Field(None, max_length=50)
    ts_api_key: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(
        None,
        max_length=20,
        pattern=r"^\+?[0-9\s\-()]+$",
        description="Phone number (E.164 or local format)",
    )


# ── Response Models ───────────────────────────────────


class UserResponse(BaseModel):
    """Standard user representation returned by auth endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    channel_id: Optional[str] = None
    ts_api_key: Optional[str] = None
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Wraps UserResponse for signup/login — cookies carry tokens."""

    data: UserResponse
    message: str = "Success"


class ErrorResponse(BaseModel):
    """Structured error response."""

    error: str
    message: str
