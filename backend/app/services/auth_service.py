"""Auth business logic — orchestrates Supabase Auth and user repository.

This is the services layer: no FastAPI imports, no raw SQL
(constitution Article I). Raises domain exceptions from core.exceptions.
"""

import structlog

from app.core.exceptions import (
    InvalidCredentialsError,
    ProfileUpdateError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger()


class AuthService:
    """Handles signup, login, logout, profile read/update."""

    def __init__(self, supabase, supabase_admin):
        self._supabase = supabase
        self._admin = supabase_admin
        self._users = UserRepository(supabase_admin)

    async def signup(
        self,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> dict:
        """Create a new user via Supabase Auth and insert a users row.

        Sets app_metadata.role = 'user' (not user_metadata — Supabase
        skill rule: user_metadata is user-writable and untrusted).
        """
        try:
            auth_response = await self._admin.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "data": {"full_name": full_name or ""},
                    },
                }
            )
        except Exception as exc:
            logger.warning("signup_failed", email=email, error=str(exc))
            raise UserAlreadyExistsError() from exc

        user = auth_response.user
        if not user:
            raise UserAlreadyExistsError()

        # Set role in app_metadata (authoritative source for permissions)
        await self._admin.auth.admin.update_user_by_id(
            user.id,
            {"app_metadata": {"role": "user"}},
        )

        # Create the public.users row
        user_data = {
            "id": user.id,
            "email": email,
            "full_name": full_name,
            "role": "user",
        }
        try:
            await self._users.create_user(user_data)
        except Exception as exc:
            logger.error("signup_profile_creation_failed", user_id=user.id, error=str(exc))
            try:
                await self._admin.auth.admin.delete_user(user.id)
                logger.info("signup_rollback_success", user_id=user.id)
            except Exception as rollback_exc:
                logger.critical("signup_rollback_failed", user_id=user.id, error=str(rollback_exc))
            raise exc

        session = auth_response.session
        logger.info("user_signed_up", user_id=user.id)

        return {
            "user": user_data,
            "access_token": session.access_token if session else "",
            "refresh_token": session.refresh_token if session else "",
        }

    async def login(self, email: str, password: str) -> dict:
        """Authenticate via Supabase Auth and return tokens + profile."""
        try:
            auth_response = await self._admin.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            logger.warning("login_failed", email=email)
            raise InvalidCredentialsError() from exc

        user = auth_response.user
        session = auth_response.session
        if not user or not session:
            raise InvalidCredentialsError()

        # Fetch the full profile from our users table
        profile = await self._users.get_user_by_id(user.id)
        if not profile:
            # Edge case: auth user exists but users row doesn't
            profile = {
                "id": user.id,
                "email": email,
                "role": "user",
            }

        logger.info("user_logged_in", user_id=user.id)

        return {
            "user": profile,
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }

    async def logout(self, user_id: str) -> None:
        """Revoke all sessions for this user server-side.

        Uses scope='global' to invalidate every session — per the
        Supabase skill: "revoke sessions explicitly on account deletion."
        """
        try:
            # Sign out all sessions via admin API
            await self._admin.auth.admin.sign_out(user_id, scope="global")
        except Exception:
            # If sign-out fails, log but don't block (cookies get cleared
            # on the response anyway)
            logger.warning("logout_revoke_failed", user_id=user_id)

        logger.info("user_logged_out", user_id=user_id)

    async def get_profile(self, user_id: str) -> dict:
        """Fetch the user's profile from the users table."""
        profile = await self._users.get_user_by_id(user_id)
        if not profile:
            raise UserNotFoundError()
        return profile

    async def update_profile(
        self, user_id: str, updates: dict
    ) -> dict:
        """Update allowed profile fields.

        Only channel_id, ts_api_key, phone, and full_name are editable.
        The 'role' field is never updatable via this endpoint.
        """
        allowed = {"full_name", "channel_id", "ts_api_key", "phone"}
        safe_updates = {k: v for k, v in updates.items() if k in allowed}

        if not safe_updates:
            raise ProfileUpdateError("No valid fields to update")

        profile = await self._users.update_user(user_id, safe_updates)
        if not profile:
            raise ProfileUpdateError()

        logger.info(
            "profile_updated",
            user_id=user_id,
            fields=list(safe_updates.keys()),
        )
        return profile
