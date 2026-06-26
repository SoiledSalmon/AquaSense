"""Readings repository — data access layer for the readings hypertable.

Uses the Supabase client with parameterized queries/constructs.
No business logic (constitution Article I).
"""

from datetime import datetime
import structlog

logger = structlog.get_logger()


class ReadingsRepository:
    """CRUD operations on the public.readings hypertable via Supabase client."""

    def __init__(self, supabase_client):
        self._client = supabase_client

    async def insert_reading(self, reading_data: dict) -> dict:
        """Insert a new reading row. Returns the created record."""
        data = {**reading_data}
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        if "id" in data and data["id"] is None:
            data.pop("id")

        response = (
            self._client.table("readings")
            .insert(data)
            .execute()
        )
        if not response.data:
            logger.error("reading_insert_failed", user_id=reading_data.get("user_id"))
            raise Exception("Failed to insert reading")
        return response.data[0]

    async def get_latest_reading_timestamp(self, user_id: str) -> datetime | None:
        """Get the timestamp of the latest reading for a user."""
        response = (
            self._client.table("readings")
            .select("timestamp")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        
        timestamp_str = response.data[0]["timestamp"]
        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    async def get_latest_reading(self, user_id: str) -> dict | None:
        """Get the latest reading + computed metrics for a user."""
        response = (
            self._client.table("readings")
            .select("*")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    async def get_hourly_readings(self, user_id: str, limit: int = 24) -> list[dict]:
        """Get hourly aggregated readings for the user, in chronological order."""
        response = (
            self._client.table("readings_hourly")
            .select("*")
            .eq("user_id", user_id)
            .order("bucket", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        data.reverse()
        return data

    async def get_daily_readings(self, user_id: str, limit: int = 30) -> list[dict]:
        """Get daily aggregated readings for the user, in chronological order."""
        response = (
            self._client.table("readings_daily")
            .select("*")
            .eq("user_id", user_id)
            .order("bucket", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        data.reverse()
        return data
