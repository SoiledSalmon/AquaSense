"""Alerts Router.

FastAPI endpoints for fetching user alerts, acknowledging warnings,
resolving alerts, and managing read/unread states.
"""

from typing import Annotated
from datetime import datetime, timezone
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import get_current_user, get_supabase_admin
from app.repositories.alert_repository import AlertRepository

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["alerts"])


def _get_alert_repo(supabase_admin=Depends(get_supabase_admin)) -> AlertRepository:
    """Dependency injector to obtain the AlertRepository with the admin client.

    Using the admin client allows performing writes and queries bypassing RLS issues.
    Ownership checks are strictly validated at the endpoint level using user_id.
    """
    return AlertRepository(supabase_admin)


@router.get("/alerts", status_code=status.HTTP_200_OK)
async def get_alerts(
    current_user: Annotated[dict, Depends(get_current_user)],
    status_filter: str = Query(
        "unacknowledged",
        alias="status",
        pattern="^(all|unread|unacknowledged|resolved|active)$",
    ),
    limit: int = Query(50, ge=1, le=100),
    repo: AlertRepository = Depends(_get_alert_repo),
):
    """Retrieve alerts for the authenticated user, optionally filtered by status."""
    user_id = current_user["sub"]
    try:
        alerts = await repo.get_alerts(user_id, status=status_filter, limit=limit)
        return {"status": status_filter, "alerts": alerts}
    except Exception as e:
        logger.error(
            "api_get_alerts_failed", user_id=user_id, status=status_filter, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch alerts",
        )


@router.post("/alerts/{alert_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge_alert(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: AlertRepository = Depends(_get_alert_repo),
):
    """Acknowledge an active water warning alert."""
    user_id = current_user["sub"]
    try:
        # Check ownership first
        alert = await repo.get_alert(alert_id, user_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        updates = {
            "is_acknowledged": True,
            "acknowledged_at": datetime.now(timezone.utc),
            "is_read": True,  # Acknowledging automatically marks as read
        }
        updated_alert = await repo.update_alert(alert_id, user_id, updates)
        logger.info("api_alert_acknowledged", alert_id=alert_id, user_id=user_id)
        return {"success": True, "alert": updated_alert}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_acknowledge_alert_failed",
            alert_id=alert_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge alert",
        )


@router.post("/alerts/{alert_id}/resolve", status_code=status.HTTP_200_OK)
async def resolve_alert(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: AlertRepository = Depends(_get_alert_repo),
):
    """Mark an alert as resolved when telemetry returns to normal."""
    user_id = current_user["sub"]
    try:
        # Check ownership first
        alert = await repo.get_alert(alert_id, user_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        updates = {
            "is_resolved": True,
            "resolved_at": datetime.now(timezone.utc),
            "is_read": True,  # Resolving also marks as read
        }
        updated_alert = await repo.update_alert(alert_id, user_id, updates)
        logger.info("api_alert_resolved", alert_id=alert_id, user_id=user_id)
        return {"success": True, "alert": updated_alert}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_resolve_alert_failed", alert_id=alert_id, user_id=user_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert",
        )


@router.post("/alerts/{alert_id}/read", status_code=status.HTTP_200_OK)
async def mark_alert_read(
    alert_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: AlertRepository = Depends(_get_alert_repo),
):
    """Mark a notification alert as read."""
    user_id = current_user["sub"]
    try:
        # Check ownership first
        alert = await repo.get_alert(alert_id, user_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )

        updates = {"is_read": True}
        updated_alert = await repo.update_alert(alert_id, user_id, updates)
        logger.info("api_alert_marked_read", alert_id=alert_id, user_id=user_id)
        return {"success": True, "alert": updated_alert}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_mark_alert_read_failed",
            alert_id=alert_id,
            user_id=user_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark alert as read",
        )
