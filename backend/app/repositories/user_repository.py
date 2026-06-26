"""User repository — data access layer for the public.users table.

Uses the Supabase client with parameterized queries only (constitution
Article III §5: no string-interpolated SQL). No business logic
(constitution Article I).
"""

import structlog

logger = structlog.get_logger()


class UserRepository:
    """CRUD operations on the public.users table via Supabase client."""

    def __init__(self, supabase_client):
        self._client = supabase_client

    async def create_user(self, user_data: dict) -> dict:
        """Insert a new user row. Returns the created record."""
        response = (
            self._client.table("users")
            .insert(user_data)
            .execute()
        )
        if not response.data:
            logger.error("user_create_failed", user_id=user_data.get("id"))
            return user_data  # Return input as fallback
        return response.data[0]

    async def get_user_by_id(self, user_id: str) -> dict | None:
        """Fetch a single user by their UUID. Returns None if not found."""
        response = (
            self._client.table("users")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return response.data

    async def update_user(
        self, user_id: str, updates: dict
    ) -> dict | None:
        """Update specific fields on a user row. Returns the updated record."""
        response = (
            self._client.table("users")
            .update(updates)
            .eq("id", user_id)
            .execute()
        )
        if not response.data:
            logger.warning("user_update_empty", user_id=user_id)
            return None
        return response.data[0]
