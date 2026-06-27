"""Admin repository — data access layer for admin operations.

Uses the Supabase client with parameterized queries only (constitution Article III §5).
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


class AdminRepository:
    """Provides administrative data access across all user accounts."""

    def __init__(self, supabase_client):
        self._client = supabase_client

    async def get_users(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch users with search, role filtering, pagination, and sorting."""
        query = self._client.table("users").select("*")

        if role and role != "all":
            query = query.eq("role", role)
        if search:
            query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")

        offset = (page - 1) * limit
        query = query.order(sort_by, desc=(order == "desc")).range(offset, offset + limit - 1)
        response = await query.execute()
        return response.data or []

    async def get_users_count(self, search: Optional[str] = None, role: Optional[str] = None) -> int:
        """Count users matching search and role parameters."""
        query = self._client.table("users").select("id", count="exact")

        if role and role != "all":
            query = query.eq("role", role)
        if search:
            query = query.or_(f"email.ilike.%{search}%,full_name.ilike.%{search}%")

        response = await query.limit(1).execute()
        return response.count or 0

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single user profile."""
        response = await (
            self._client.table("users")
            .select("*")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        # postgrest-py's maybe_single() returns None directly (instead of a response
        # object with empty data) when zero rows match the query.
        return response.data if response else None

    async def update_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        """Update a user's role in the public.users table."""
        response = await (
            self._client.table("users")
            .update({"role": role})
            .eq("id", user_id)
            .execute()
        )
        if not response.data:
            logger.error("admin_repo_update_role_failed", user_id=user_id, role=role)
            raise Exception("Failed to update user role")
        return response.data[0]

    async def get_readings(
        self,
        user_id: Optional[str] = None,
        label: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch telemetry readings across all users, joining user email."""
        query = self._client.table("readings").select("*, users(email)")

        if user_id:
            query = query.eq("user_id", user_id)
        if label and label != "all":
            query = query.eq("label", label)

        offset = (page - 1) * limit
        query = query.order("timestamp", desc=True).range(offset, offset + limit - 1)
        response = await query.execute()
        return response.data or []

    async def get_readings_count(self, user_id: Optional[str] = None, label: Optional[str] = None) -> int:
        """Count telemetry readings across all users matching filters."""
        query = self._client.table("readings").select("id", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)
        if label and label != "all":
            query = query.eq("label", label)

        response = await query.limit(1).execute()
        return response.count or 0

    async def get_alerts(
        self,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        is_acknowledged: Optional[bool] = None,
        is_resolved: Optional[bool] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch alerts across all users, joining user email."""
        query = self._client.table("alerts").select("*, users(email)")

        if user_id:
            query = query.eq("user_id", user_id)
        if severity and severity != "all":
            query = query.eq("severity", severity)
        if is_acknowledged is not None:
            query = query.eq("is_acknowledged", is_acknowledged)
        if is_resolved is not None:
            query = query.eq("is_resolved", is_resolved)

        offset = (page - 1) * limit
        query = query.order("timestamp", desc=True).range(offset, offset + limit - 1)
        response = await query.execute()
        return response.data or []

    async def get_alerts_count(
        self,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        is_acknowledged: Optional[bool] = None,
        is_resolved: Optional[bool] = None,
    ) -> int:
        """Count alerts across all users matching filters."""
        query = self._client.table("alerts").select("id", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)
        if severity and severity != "all":
            query = query.eq("severity", severity)
        if is_acknowledged is not None:
            query = query.eq("is_acknowledged", is_acknowledged)
        if is_resolved is not None:
            query = query.eq("is_resolved", is_resolved)

        response = await query.limit(1).execute()
        return response.count or 0

    async def get_ml_predictions(
        self,
        user_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        is_anomaly: Optional[bool] = None,
        page: int = 1,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Fetch ML predictions across all users, joining user email."""
        query = self._client.table("ml_results").select("*, users(email)")

        if user_id:
            query = query.eq("user_id", user_id)
        if risk_level and risk_level != "all":
            query = query.eq("risk_level", risk_level)
        if is_anomaly is not None:
            query = query.eq("is_anomaly", is_anomaly)

        offset = (page - 1) * limit
        query = query.order("timestamp", desc=True).range(offset, offset + limit - 1)
        response = await query.execute()
        return response.data or []

    async def get_ml_predictions_count(
        self,
        user_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        is_anomaly: Optional[bool] = None,
    ) -> int:
        """Count ML predictions across all users matching filters."""
        query = self._client.table("ml_results").select("id", count="exact")

        if user_id:
            query = query.eq("user_id", user_id)
        if risk_level and risk_level != "all":
            query = query.eq("risk_level", risk_level)
        if is_anomaly is not None:
            query = query.eq("is_anomaly", is_anomaly)

        response = await query.limit(1).execute()
        return response.count or 0

    async def get_stats_rpc(self) -> Optional[Dict[str, Any]]:
        """Call the RPC database function get_admin_dashboard_stats.

        Returns None if the RPC does not exist or fails.
        """
        try:
            response = await self._client.rpc("get_admin_dashboard_stats").execute()
            return response.data
        except Exception as e:
            logger.warning("get_stats_rpc_failed", error=str(e))
            return None

    async def get_stats_fallback(self) -> Dict[str, Any]:
        """Python fallback to compute aggregated stats if the RPC is unavailable."""
        logger.info("get_stats_fallback_running")

        # 1. Total readings & Active users
        readings_cnt_res = await self._client.table("readings").select("id, user_id", count="exact").execute()
        total_readings = readings_cnt_res.count or 0
        
        # Calculate distinct active users
        active_users_res = await self._client.table("users").select("id", count="exact").not_.is_("channel_id", "null").execute()
        active_users = active_users_res.count or 0

        # 2. Unsafe events
        unsafe_cnt_res = await self._client.table("readings").select("id", count="exact").eq("label", "unsafe").execute()
        unsafe_events = unsafe_cnt_res.count or 0

        # 3. Average WQI
        # Query recent 1000 readings to calculate avg WQI defensively
        wqi_res = await self._client.table("readings").select("wqi_score").order("timestamp", desc=True).limit(1000).execute()
        wqi_scores = [r["wqi_score"] for r in (wqi_res.data or []) if r.get("wqi_score") is not None]
        avg_wqi = sum(wqi_scores) / len(wqi_scores) if wqi_scores else 0.0

        # 4. Alerts frequency
        now = datetime.now(timezone.utc)
        yesterday = (now - timedelta(days=1)).isoformat()
        week_ago = (now - timedelta(days=7)).isoformat()

        alerts_24h = (await self._client.table("alerts").select("id", count="exact").gte("timestamp", yesterday).execute()).count or 0
        alerts_7d = (await self._client.table("alerts").select("id", count="exact").gte("timestamp", week_ago).execute()).count or 0

        # 5. ML distribution
        anomaly_count = (await self._client.table("ml_results").select("id", count="exact").eq("is_anomaly", True).execute()).count or 0
        normal_count = (await self._client.table("ml_results").select("id", count="exact").eq("is_anomaly", False).execute()).count or 0

        low_risk = (await self._client.table("ml_results").select("id", count="exact").eq("risk_level", "low").execute()).count or 0
        medium_risk = (await self._client.table("ml_results").select("id", count="exact").eq("risk_level", "medium").execute()).count or 0
        high_risk = (await self._client.table("ml_results").select("id", count="exact").eq("risk_level", "high").execute()).count or 0

        # 6. Trends (Last 7 days daily averages)
        trends_res = await self._client.table("readings_daily").select("bucket, avg_wqi").order("bucket", desc=True).limit(30).execute()
        trends_data = trends_res.data or []
        trends_data.reverse()

        trends = []
        for t in trends_data:
            # Clean up bucket timestamp string
            bucket_str = t.get("bucket", "")
            date_part = bucket_str.split("T")[0] if "T" in bucket_str else bucket_str
            trends.append({
                "date": date_part,
                "avg_wqi": t.get("avg_wqi"),
                "readings_count": 0  # Placeholder in fallback
            })

        return {
            "active_users_count": active_users,
            "total_readings_count": total_readings,
            "unsafe_events_count": unsafe_events,
            "average_wqi": round(avg_wqi, 2),
            "alert_frequency": {
                "last_24h": alerts_24h,
                "last_7d": alerts_7d
            },
            "ml_prediction_distribution": {
                "anomaly_count": anomaly_count,
                "normal_count": normal_count,
                "low_risk": low_risk,
                "medium_risk": medium_risk,
                "high_risk": high_risk
            },
            "trends": trends
        }
