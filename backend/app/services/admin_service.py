"""Admin service — coordinates business logic for Phase 6 admin features.

Handles role synchronization, user deletion via Supabase admin client,
and system status checks (constitution Article I: Services layer).
"""

from typing import Any, Dict, List, Optional
import structlog
from fastapi import Request

from app.core.exceptions import (
    UserNotFoundError,
    ProfileUpdateError,
)
from app.repositories.admin_repository import AdminRepository

logger = structlog.get_logger()


class AdminService:
    """Orchestrates administrative tasks, database queries, and system status checks."""

    def __init__(self, supabase_client, supabase_admin):
        self._supabase = supabase_client
        self._admin = supabase_admin
        self._repo = AdminRepository(supabase_client)

    async def get_users_list(
        self,
        search: Optional[str] = None,
        role: Optional[str] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get paginated list of users and the total count."""
        users = await self._repo.get_users(
            search=search,
            role=role,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit,
        )
        total_count = await self._repo.get_users_count(search=search, role=role)
        return {
            "users": users,
            "total_count": total_count,
            "page": page,
            "limit": limit,
        }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Fetch details of a single user profile."""
        profile = await self._repo.get_user_by_id(user_id)
        if not profile:
            raise UserNotFoundError()
        return profile

    async def update_user_role(self, user_id: str, new_role: str) -> Dict[str, Any]:
        """Atomically update user role in public.users and Auth app_metadata.

        Ensures security alignment (ADR 002).
        """
        # 1. Verify user exists
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        # 2. Update Supabase Auth app_metadata via admin client
        try:
            await self._admin.auth.admin.update_user_by_id(
                user_id,
                {"app_metadata": {"role": new_role}},
            )
        except Exception as exc:
            logger.error("admin_service_auth_role_update_failed", user_id=user_id, role=new_role, error=str(exc))
            raise ProfileUpdateError("Failed to update user role in auth database") from exc

        # 3. Update public.users table role
        updated_profile = await self._repo.update_user_role(user_id, new_role)
        logger.info("user_role_synchronized", user_id=user_id, role=new_role)
        return updated_profile

    async def delete_user(self, user_id: str) -> None:
        """Revoke all sessions and delete the user from Supabase Auth.

        Foreign key constraints with ON DELETE CASCADE will automatically
        purge the users table profile, readings, alerts, and ML results.
        """
        # Verify user exists first
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError()

        try:
            # Revoke all current tokens/sessions
            await self._admin.auth.admin.sign_out(user_id, scope="global")
        except Exception as exc:
            # Log failure to sign out but proceed with deletion
            logger.warning("admin_service_sign_out_before_delete_failed", user_id=user_id, error=str(exc))

        try:
            # Delete user via admin client
            await self._admin.auth.admin.delete_user(user_id)
            logger.info("user_permanently_deleted", user_id=user_id)
        except Exception as exc:
            logger.error("admin_service_delete_user_failed", user_id=user_id, error=str(exc))
            raise ProfileUpdateError("Failed to delete user account") from exc

    async def get_readings_history(
        self,
        user_id: Optional[str] = None,
        label: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch globalTelemetry readings history with total count and joined user email."""
        readings = await self._repo.get_readings(
            user_id=user_id,
            label=label,
            page=page,
            limit=limit,
        )
        total_count = await self._repo.get_readings_count(user_id=user_id, label=label)

        # Flatten joined users email
        flat_readings = []
        for r in readings:
            email = r.get("users", {}).get("email") if r.get("users") else None
            flat_r = {**r}
            flat_r.pop("users", None)
            flat_r["user_email"] = email
            flat_readings.append(flat_r)

        return {
            "readings": flat_readings,
            "total_count": total_count,
            "page": page,
            "limit": limit,
        }

    async def get_alerts_list(
        self,
        user_id: Optional[str] = None,
        severity: Optional[str] = None,
        is_acknowledged: Optional[bool] = None,
        is_resolved: Optional[bool] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch global alerts list with total count."""
        alerts = await self._repo.get_alerts(
            user_id=user_id,
            severity=severity,
            is_acknowledged=is_acknowledged,
            is_resolved=is_resolved,
            page=page,
            limit=limit,
        )
        total_count = await self._repo.get_alerts_count(
            user_id=user_id,
            severity=severity,
            is_acknowledged=is_acknowledged,
            is_resolved=is_resolved,
        )

        # Flatten user email
        flat_alerts = []
        for a in alerts:
            email = a.get("users", {}).get("email") if a.get("users") else None
            flat_a = {**a}
            flat_a.pop("users", None)
            flat_a["user_email"] = email
            flat_alerts.append(flat_a)

        return {
            "alerts": flat_alerts,
            "total_count": total_count,
            "page": page,
            "limit": limit,
        }

    async def get_ml_predictions_list(
        self,
        user_id: Optional[str] = None,
        risk_level: Optional[str] = None,
        is_anomaly: Optional[bool] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Fetch global ML predictions with total count."""
        predictions = await self._repo.get_ml_predictions(
            user_id=user_id,
            risk_level=risk_level,
            is_anomaly=is_anomaly,
            page=page,
            limit=limit,
        )
        total_count = await self._repo.get_ml_predictions_count(
            user_id=user_id,
            risk_level=risk_level,
            is_anomaly=is_anomaly,
        )

        # Flatten user email
        flat_preds = []
        for p in predictions:
            email = p.get("users", {}).get("email") if p.get("users") else None
            flat_p = {**p}
            flat_p.pop("users", None)
            flat_p["user_email"] = email
            flat_preds.append(flat_p)

        return {
            "predictions": flat_preds,
            "total_count": total_count,
            "page": page,
            "limit": limit,
        }

    async def get_stats(self, request: Request) -> Dict[str, Any]:
        """Compile administrator dashboard aggregated statistics and system status."""
        stats = await self._repo.get_stats_rpc()
        if not stats:
            stats = await self._repo.get_stats_fallback()

        # Compile system health status
        stats["system_status"] = await self.get_system_status(request)
        return stats

    async def get_system_status(self, request: Request) -> Dict[str, str]:
        """Check database accessibility and background MQTT subscriber connection state."""
        db_status = "healthy"
        try:
            # Ping database with a simple query
            await self._supabase.table("users").select("id").limit(1).execute()
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            db_status = "unhealthy"

        mqtt_status = "unknown"
        if request.app and hasattr(request.app, "state") and hasattr(request.app.state, "mqtt_status"):
            mqtt_status = request.app.state.mqtt_status

        return {
            "database": db_status,
            "mqtt_subscriber": mqtt_status,
        }
