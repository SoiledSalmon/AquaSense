"""Readings Router.

FastAPI endpoints for streaming live telemetry, retrieving the latest telemetry reading,
and fetching historical aggregated sensor readings from continuous aggregates.
"""

from typing import Annotated
import json
import asyncio
from datetime import datetime
import structlog

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from app.core.dependencies import get_current_user, get_supabase_admin
from app.repositories.readings_repository import ReadingsRepository
from app.services.sse_manager import sse_manager

logger = structlog.get_logger()

router = APIRouter(prefix="/api", tags=["readings"])


def _get_readings_repo(
    supabase_admin=Depends(get_supabase_admin),
) -> ReadingsRepository:
    """Dependency injector to obtain the ReadingsRepository with an admin client.

    Using the admin client allows querying the materialized views bypassing RLS issues.
    Strict user filtering is applied directly at the database queries.
    """
    return ReadingsRepository(supabase_admin)


@router.get("/readings/latest", status_code=status.HTTP_200_OK)
async def get_latest_reading(
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: ReadingsRepository = Depends(_get_readings_repo),
):
    """Retrieve the single latest sensor reading for the authenticated user."""
    user_id = current_user["sub"]
    try:
        reading = await repo.get_latest_reading(user_id)
        return {"reading": reading}
    except Exception as e:
        logger.error("api_get_latest_reading_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch latest reading",
        )


@router.get("/readings", status_code=status.HTTP_200_OK)
async def get_readings_history(
    current_user: Annotated[dict, Depends(get_current_user)],
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    repo: ReadingsRepository = Depends(_get_readings_repo),
):
    """Retrieve aggregated readings history for the user based on range ('24h', '7d', '30d')."""
    user_id = current_user["sub"]
    try:
        if range == "24h":
            # Last 24 hourly buckets
            data = await repo.get_hourly_readings(user_id, limit=24)
        elif range == "7d":
            # Last 7 daily buckets
            data = await repo.get_daily_readings(user_id, limit=7)
        elif range == "30d":
            # Last 30 daily buckets
            data = await repo.get_daily_readings(user_id, limit=30)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid range parameter. Supported: 24h, 7d, 30d",
            )
        return {"range": range, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_get_readings_history_failed",
            user_id=user_id,
            range=range,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch readings history",
        )


@router.get("/stream")
async def stream_telemetry(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    repo: ReadingsRepository = Depends(_get_readings_repo),
):
    """Establish a Server-Sent Events stream for real-time telemetry updates."""
    user_id = current_user["sub"]
    queue = await sse_manager.connect(user_id)

    async def event_generator():
        # 1. Yield initial state (latest reading + any unread alerts)
        try:
            latest_reading = await repo.get_latest_reading(user_id)
            if latest_reading:
                # Format datetimes to ISO strings for JSON serialisation
                for k, v in latest_reading.items():
                    if isinstance(v, datetime):
                        latest_reading[k] = v.isoformat()
                yield f"event: reading_update\ndata: {json.dumps(latest_reading)}\n\n"
        except Exception as e:
            logger.error(
                "sse_send_initial_reading_failed", user_id=user_id, error=str(e)
            )

        try:
            # Query unread alerts (fail-safe fallback if table is missing)
            alerts_response = await (
                repo._client.table("alerts")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_read", False)
                .execute()
            )
            unread_alerts = alerts_response.data or []
            for alert in unread_alerts:
                yield f"event: alert_new\ndata: {json.dumps(alert)}\n\n"
        except Exception as e:
            logger.warning(
                "sse_send_initial_alerts_warning", user_id=user_id, error=str(e)
            )

        # 2. Main subscriber loop
        try:
            while True:
                if await request.is_disconnected():
                    logger.info("sse_disconnected_by_client", user_id=user_id)
                    break

                try:
                    # Timeout after 30s to trigger heartbeat
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    event_type = event["event"]
                    event_data = event["data"]

                    # Serialize any datetime fields
                    if isinstance(event_data, dict):
                        for k, v in event_data.items():
                            if isinstance(v, datetime):
                                event_data[k] = v.isoformat()

                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
                    queue.task_done()
                except asyncio.TimeoutError:
                    # Connection keep-alive heartbeat
                    yield f"event: heartbeat\ndata: {json.dumps({'status': 'alive'})}\n\n"
        except asyncio.CancelledError:
            logger.info("sse_stream_cancelled", user_id=user_id)
        finally:
            await sse_manager.disconnect(user_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
