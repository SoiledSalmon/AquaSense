"""Alert Repository.

Data access layer for managing alert records in the Supabase database.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
import structlog

logger = structlog.get_logger()


class AlertRepository:
    """Repository for managing alert records in the database."""

    def __init__(self, supabase_client):
        self._client = supabase_client

    async def create_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a new alert into the database."""
        data = {**alert_data}
        if isinstance(data.get("timestamp"), datetime):
            data["timestamp"] = data["timestamp"].isoformat()
        if isinstance(data.get("acknowledged_at"), datetime):
            data["acknowledged_at"] = data["acknowledged_at"].isoformat()
        if isinstance(data.get("resolved_at"), datetime):
            data["resolved_at"] = data["resolved_at"].isoformat()

        response = (
            self._client.table("alerts")
            .insert(data)
            .execute()
        )
        if not response.data:
            logger.error("alert_insert_failed", user_id=alert_data.get("user_id"))
            raise Exception("Failed to insert alert")
        return response.data[0]

    async def get_alerts(self, user_id: str, status: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve alerts for the user, filtered by status."""
        query = self._client.table("alerts").select("*").eq("user_id", user_id)

        status_lower = status.lower()
        if status_lower == "unread":
            query = query.eq("is_read", False)
        elif status_lower == "unacknowledged":
            query = query.eq("is_acknowledged", False)
        elif status_lower == "resolved":
            query = query.eq("is_resolved", True)
        elif status_lower == "active":
            # Active means either not acknowledged or not resolved
            query = query.or_("is_acknowledged.eq.false,is_resolved.eq.false")

        response = query.order("timestamp", desc=True).limit(limit).execute()
        return response.data or []

    async def get_alert(self, alert_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single alert by ID, verifying user ownership."""
        response = (
            self._client.table("alerts")
            .select("*")
            .eq("id", alert_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]

    async def update_alert(self, alert_id: str, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an alert's columns, verifying user ownership."""
        formatted_updates = {}
        for k, v in updates.items():
            if isinstance(v, datetime):
                formatted_updates[k] = v.isoformat()
            else:
                formatted_updates[k] = v

        response = (
            self._client.table("alerts")
            .update(formatted_updates)
            .eq("id", alert_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not response.data:
            logger.error("alert_update_failed", alert_id=alert_id, user_id=user_id)
            raise Exception("Failed to update alert or alert not found")
        return response.data[0]

    async def get_latest_alert_by_category(self, user_id: str, category: str) -> Optional[Dict[str, Any]]:
        """Get the most recent alert of a specific category for a user (used for cooldown checks)."""
        response = (
            self._client.table("alerts")
            .select("*")
            .eq("user_id", user_id)
            .eq("category", category)
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]
