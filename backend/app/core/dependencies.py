"""FastAPI dependency functions for authentication and Supabase clients.

get_current_user is injected via Depends() on every protected route.
Supabase clients are initialised once at startup (lifespan) and stored
on app.state — dependencies retrieve them from there.
"""

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Request, Response

from app.core.config import Settings, get_settings
from app.core.security import verify_jwt


async def get_current_user(
    request: Request,
    response: Response,
    access_token: Annotated[str | None, Cookie()] = None,
    refresh_token: Annotated[str | None, Cookie()] = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Extract and verify JWT from the access_token httpOnly cookie.

    If the access token is expired or invalid, it attempts to transparently
    refresh it using the refresh_token cookie, updating response cookies.
    Returns the decoded user claims dictionary.
    """
    if access_token:
        try:
            return verify_jwt(access_token, settings)
        except Exception:
            # If access_token is invalid/expired, fall through to refresh
            pass

    # No valid access token, try refreshing using refresh token
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        supabase = request.app.state.supabase
        auth_response = await supabase.auth.refresh_session(refresh_token)
        session = auth_response.session
        user = auth_response.user

        if not session or not user:
            raise HTTPException(status_code=401, detail="Session expired")

        # Set the refreshed cookies
        from app.core.security import (
            ACCESS_TOKEN_MAX_AGE,
            REFRESH_TOKEN_MAX_AGE,
            create_cookie_params,
        )
        cookie_params = create_cookie_params(settings)
        response.set_cookie(
            key="access_token",
            value=session.access_token,
            max_age=ACCESS_TOKEN_MAX_AGE,
            **cookie_params,
        )
        response.set_cookie(
            key="refresh_token",
            value=session.refresh_token,
            max_age=REFRESH_TOKEN_MAX_AGE,
            **cookie_params,
        )

        return {
            "sub": user.id,
            "email": user.email,
            "role": user.app_metadata.get("role", "user") if user.app_metadata else "user",
            "app_metadata": user.app_metadata or {},
            "user_metadata": user.user_metadata or {},
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired")


def get_supabase_client(request: Request):
    """Return the Supabase client (anon key) from app state.

    Used for standard data operations that respect RLS.
    """
    return request.app.state.supabase


def get_supabase_admin(request: Request):
    """Return the Supabase admin client (service-role key) from app state.

    Used for operations that bypass RLS — signup user creation,
    app_metadata updates, session revocation. NEVER exposed to frontend.
    """
    return request.app.state.supabase_admin


async def get_current_admin(
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Verify that the current user has the admin role.

    Checks the 'role' field from the claims dictionary, falling back
    to app_metadata.role if 'role' is 'authenticated' or missing.
    Raises a 403 Forbidden HTTP exception if the user is not an admin.
    """
    role = current_user.get("role")
    if not role or role == "authenticated":
        app_metadata = current_user.get("app_metadata", {})
        role = app_metadata.get("role", "user") if isinstance(app_metadata, dict) else "user"

    if role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Administrator access required"
        )
    return current_user

