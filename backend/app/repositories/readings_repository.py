"""Readings repository — data access layer for the readings hypertable.

Uses the Supabase client with parameterized queries/constructs.
"""

from datetime import datetime
import structlog

logger = structlog.get_logger()


# TODO: [TECH-DEBT-001] Currently using plain Postgres 17 materialized views instead of TimescaleDB hypertables.
# Deferred due to PG15/PG17 version mismatch risk; revisit before scaling beyond development/demo volume.
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

        response = await self._client.table("readings").insert(data).execute()
        if not response.data:
            logger.error("reading_insert_failed", user_id=reading_data.get("user_id"))
            raise Exception("Failed to insert reading")
        return response.data[0]

    async def get_latest_reading_timestamp(self, user_id: str) -> datetime | None:
        """Get the timestamp of the latest reading for a user."""
        response = await (
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
        response = await (
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
        response = await (
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
        response = await (
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

    async def update_reading_ml(
        self, reading_id: str, wqi_score: float, label: str
    ) -> dict:
        """Update a reading row with computed WQI score and classification label."""
        response = await (
            self._client.table("readings")
            .update({"wqi_score": wqi_score, "label": label})
            .eq("id", reading_id)
            .execute()
        )
        if not response.data:
            logger.error("reading_update_ml_failed", reading_id=reading_id)
            raise Exception("Failed to update reading WQI/label")
        return response.data[0]

    async def insert_ml_result(self, result_data: dict) -> dict:
        """Insert a new machine learning result row."""
        data = {**result_data}
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        response = await self._client.table("ml_results").insert(data).execute()
        if not response.data:
            logger.error(
                "ml_result_insert_failed", reading_id=result_data.get("reading_id")
            )
            raise Exception("Failed to insert ML result")
        return response.data[0]

    async def create_alert(self, alert_data: dict) -> dict:
        """Create a new water contaminant alert."""
        data = {**alert_data}
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        response = await self._client.table("alerts").insert(data).execute()
        if not response.data:
            logger.error("create_alert_failed", user_id=alert_data.get("user_id"))
            raise Exception("Failed to create alert")
        return response.data[0]

    async def get_recent_readings(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get recent raw readings for the user (returned in chronological order)."""
        response = await (
            self._client.table("readings")
            .select("ph, tds, turbidity, timestamp")
            .eq("user_id", user_id)
            .order("timestamp", desc=True)
            .limit(limit)
            .execute()
        )
        data = response.data or []
        data.reverse()
        return data
