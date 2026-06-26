"""Auth router — PRD §7.2 endpoints.

Handles request parsing, cookie management, rate limiting, and
status codes. Delegates all business logic to AuthService
(constitution Article I: API layer may NOT contain business logic).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.schemas.auth_schemas import (
    AuthResponse,
    LoginRequest,
    ProfileUpdateRequest,
    SignupRequest,
    UserResponse,
)
from app.core.config import Settings, get_settings
from app.core.dependencies import (
    get_current_user,
    get_supabase_admin,
    get_supabase_client,
)
from app.core.security import (
    ACCESS_TOKEN_MAX_AGE,
    REFRESH_TOKEN_MAX_AGE,
    create_cookie_params,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _get_auth_service(
    supabase=Depends(get_supabase_client),
    supabase_admin=Depends(get_supabase_admin),
) -> AuthService:
    return AuthService(supabase=supabase, supabase_admin=supabase_admin)


def _set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    settings: Settings,
) -> None:
    """Set httpOnly auth cookies on the response."""
    cookie_params = create_cookie_params(settings)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_MAX_AGE,
        **cookie_params,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=REFRESH_TOKEN_MAX_AGE,
        **cookie_params,
    )


def _clear_auth_cookies(response: Response, settings: Settings) -> None:
    """Remove auth cookies from the response."""
    cookie_params = create_cookie_params(settings)
    response.delete_cookie(key="access_token", **cookie_params)
    response.delete_cookie(key="refresh_token", **cookie_params)


# ── POST /api/auth/signup ─────────────────────────────

@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
    description="Register with email and password. Default role is 'user'.",
)
@limiter.limit("3/hour")
async def signup(
    request: Request,
    response: Response,
    body: SignupRequest,
    service: AuthService = Depends(_get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    result = await service.signup(
        email=body.email,
        password=body.password,
        full_name=body.full_name,
    )
    _set_auth_cookies(
        response,
        result["access_token"],
        result["refresh_token"],
        settings,
    )
    return AuthResponse(data=result["user"], message="Account created")


# ── POST /api/auth/login ─────────────────────────────

@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with credentials",
    description="Exchange email + password for a JWT session.",
)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    service: AuthService = Depends(_get_auth_service),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    result = await service.login(email=body.email, password=body.password)
    _set_auth_cookies(
        response,
        result["access_token"],
        result["refresh_token"],
        settings,
    )
    return AuthResponse(data=result["user"])


# ── POST /api/auth/logout ────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout and revoke session",
    description="Invalidate the current session server-side and clear cookies.",
)
async def logout(
    response: Response,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: AuthService = Depends(_get_auth_service),
    settings: Settings = Depends(get_settings),
) -> None:
    await service.logout(user_id=current_user["sub"])
    _clear_auth_cookies(response, settings)


# ── GET /api/auth/me ──────────────────────────────────

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Return the authenticated user's profile.",
)
async def get_me(
    current_user: Annotated[dict, Depends(get_current_user)],
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    profile = await service.get_profile(user_id=current_user["sub"])
    return UserResponse(**profile)


# ── PATCH /api/auth/profile ───────────────────────────

@router.patch(
    "/profile",
    response_model=UserResponse,
    summary="Update user profile",
    description="Update channel_id, ts_api_key, phone, or full_name.",
)
async def update_profile(
    body: ProfileUpdateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    updates = body.model_dump(exclude_unset=True)
    profile = await service.update_profile(
        user_id=current_user["sub"],
        updates=updates,
    )
    return UserResponse(**profile)
