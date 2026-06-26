"""Admin Router.

FastAPI endpoints exposing administrator functionalities: statistics, user management,
global readings, alerts history, and ML prediction monitoring.
"""

from typing import Annotated, Optional
import structlog

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.schemas.admin_schemas import (
    AdminStatsResponse,
    PaginatedUsersResponse,
    AdminUserResponse,
    UserUpdateRoleRequest,
    PaginatedReadingsResponse,
    PaginatedAlertsResponse,
    PaginatedMLPredictionsResponse,
)
from app.core.dependencies import (
    get_current_admin,
    get_supabase_admin,
    get_supabase_client,
)
from app.services.admin_service import AdminService

logger = structlog.get_logger()

# Protect all routes under this router by requiring admin permissions globally
router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


def _get_admin_service(
    supabase=Depends(get_supabase_client),
    supabase_admin=Depends(get_supabase_admin),
) -> AdminService:
    """Dependency injector to obtain the AdminService."""
    return AdminService(supabase_client=supabase, supabase_admin=supabase_admin)


# ── GET /api/admin/stats ──────────────────────────────

@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get system-wide metrics and trends",
    description="Retrieve high-level statistics: user activity, total readings, average WQI, alert frequency, and trends.",
)
async def get_stats(
    request: Request,
    service: AdminService = Depends(_get_admin_service),
) -> AdminStatsResponse:
    try:
        return await service.get_stats(request)
    except Exception as e:
        logger.error("admin_api_get_stats_failed", error=str(e))
        raise


# ── GET /api/admin/users ──────────────────────────────

@router.get(
    "/users",
    response_model=PaginatedUsersResponse,
    summary="List and filter users",
    description="Retrieve users with search, role filters, sorting, and pagination.",
)
async def get_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(email|full_name|role|created_at)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    service: AdminService = Depends(_get_admin_service),
) -> PaginatedUsersResponse:
    try:
        return await service.get_users_list(
            search=search,
            role=role,
            sort_by=sort_by,
            order=order,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("admin_api_get_users_failed", error=str(e))
        raise


# ── GET /api/admin/users/{user_id} ────────────────────

@router.get(
    "/users/{user_id}",
    response_model=AdminUserResponse,
    summary="Inspect user profile",
    description="Fetch a user profile by ID.",
)
async def get_user(
    user_id: str,
    service: AdminService = Depends(_get_admin_service),
) -> AdminUserResponse:
    try:
        return await service.get_user_profile(user_id)
    except Exception as e:
        logger.error("admin_api_get_user_failed", user_id=user_id, error=str(e))
        raise


# ── PATCH /api/admin/users/{user_id}/role ─────────────

@router.patch(
    "/users/{user_id}/role",
    response_model=AdminUserResponse,
    summary="Change user role",
    description="Promote or demote a user role. Syncs public database representation with auth app_metadata.",
)
async def update_user_role(
    user_id: str,
    body: UserUpdateRoleRequest,
    service: AdminService = Depends(_get_admin_service),
) -> AdminUserResponse:
    try:
        return await service.update_user_role(user_id, body.role)
    except Exception as e:
        logger.error("admin_api_update_role_failed", user_id=user_id, role=body.role, error=str(e))
        raise


# ── DELETE /api/admin/users/{user_id} ─────────────────

@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user account",
    description="Revoke all user sessions and delete user account. Cascadings delete associated telemetry data.",
)
async def delete_user(
    user_id: str,
    service: AdminService = Depends(_get_admin_service),
) -> None:
    try:
        await service.delete_user(user_id)
    except Exception as e:
        logger.error("admin_api_delete_user_failed", user_id=user_id, error=str(e))
        raise


# ── GET /api/admin/readings ───────────────────────────

@router.get(
    "/readings",
    response_model=PaginatedReadingsResponse,
    summary="Read telemetry history across all users",
    description="Retrieve paginated telemetry readings.",
)
async def get_readings(
    user_id: Optional[str] = None,
    label: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    service: AdminService = Depends(_get_admin_service),
) -> PaginatedReadingsResponse:
    try:
        return await service.get_readings_history(
            user_id=user_id,
            label=label,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("admin_api_get_readings_failed", error=str(e))
        raise


# ── GET /api/admin/alerts ─────────────────────────────

@router.get(
    "/alerts",
    response_model=PaginatedAlertsResponse,
    summary="Monitor alerts across all users",
    description="Retrieve paginated alerts list with optional severity and state filters.",
)
async def get_alerts(
    user_id: Optional[str] = None,
    severity: Optional[str] = None,
    is_acknowledged: Optional[bool] = None,
    is_resolved: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    service: AdminService = Depends(_get_admin_service),
) -> PaginatedAlertsResponse:
    try:
        return await service.get_alerts_list(
            user_id=user_id,
            severity=severity,
            is_acknowledged=is_acknowledged,
            is_resolved=is_resolved,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("admin_api_get_alerts_failed", error=str(e))
        raise


# ── GET /api/admin/ml ─────────────────────────────────

@router.get(
    "/ml",
    response_model=PaginatedMLPredictionsResponse,
    summary="Monitor ML pipeline across all users",
    description="Retrieve paginated ML results and risk score logs.",
)
async def get_ml(
    user_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_anomaly: Optional[bool] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    service: AdminService = Depends(_get_admin_service),
) -> PaginatedMLPredictionsResponse:
    try:
        return await service.get_ml_predictions_list(
            user_id=user_id,
            risk_level=risk_level,
            is_anomaly=is_anomaly,
            page=page,
            limit=limit,
        )
    except Exception as e:
        logger.error("admin_api_get_ml_failed", error=str(e))
        raise
