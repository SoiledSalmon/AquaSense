"""Tests for Phase 6 Admin APIs, Services, and Repositories.

Validates RBAC protection, user promotion/demotion role sync, and global metrics.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.core.dependencies import get_current_user
from app.api.admin_router import _get_admin_service
from app.services.admin_service import AdminService
from app.repositories.admin_repository import AdminRepository
from app.core.exceptions import UserNotFoundError


# ── 1. API Router & RBAC Tests ────────────────────────────────────────

@pytest.fixture
def mock_admin_service():
    service = MagicMock()
    service.get_stats = AsyncMock()
    service.get_users_list = AsyncMock()
    service.get_user_profile = AsyncMock()
    service.update_user_role = AsyncMock()
    service.delete_user = AsyncMock()
    service.get_readings_history = AsyncMock()
    service.get_alerts_list = AsyncMock()
    service.get_ml_predictions_list = AsyncMock()
    return service


# --- Test Case: Standard User Access (Should be Blocked) ---
def test_standard_user_blocked(mock_admin_service):
    # Override auth to return standard user role
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "user-uuid-123",
        "email": "user@example.com",
        "role": "user"
    }
    app.dependency_overrides[_get_admin_service] = lambda: mock_admin_service

    with TestClient(app) as client:
        # Standard user requests stats
        response = client.get("/api/admin/stats")
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

        # Standard user requests user list
        response = client.get("/api/admin/users")
        assert response.status_code == 403

    app.dependency_overrides.clear()


# --- Test Case: Admin Access (Should be Authorized) ---
def test_admin_authorized(mock_admin_service):
    # Override auth to return admin role
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "admin-uuid-999",
        "email": "admin@example.com",
        "role": "admin"
    }
    app.dependency_overrides[_get_admin_service] = lambda: mock_admin_service

    # Mock response
    mock_stats = {
        "active_users_count": 5,
        "total_readings_count": 120,
        "unsafe_events_count": 2,
        "average_wqi": 92.5,
        "alert_frequency": {"last_24h": 1, "last_7d": 5},
        "ml_prediction_distribution": {
            "anomaly_count": 3,
            "normal_count": 117,
            "low_risk": 115,
            "medium_risk": 3,
            "high_risk": 2
        },
        "system_status": {"database": "healthy", "mqtt_subscriber": "connected"},
        "trends": []
    }
    mock_admin_service.get_stats.return_value = mock_stats

    with TestClient(app) as client:
        response = client.get("/api/admin/stats")
        assert response.status_code == 200
        assert response.json()["active_users_count"] == 5
        assert response.json()["system_status"]["mqtt_subscriber"] == "connected"
        mock_admin_service.get_stats.assert_called_once()

    app.dependency_overrides.clear()


# ── 2. Admin Service Unit Tests ───────────────────────────────────────

@pytest.fixture
def mock_supabase():
    return MagicMock()


@pytest.fixture
def mock_supabase_admin():
    admin = MagicMock()
    admin.auth.admin.update_user_by_id = AsyncMock()
    admin.auth.admin.sign_out = AsyncMock()
    admin.auth.admin.delete_user = AsyncMock()
    return admin


@pytest.fixture
def admin_service(mock_supabase, mock_supabase_admin, monkeypatch):
    mock_repo = MagicMock()
    monkeypatch.setattr("app.services.admin_service.AdminRepository", lambda client: mock_repo)
    
    service = AdminService(mock_supabase, mock_supabase_admin)
    service._repo = mock_repo
    return service, mock_repo


@pytest.mark.asyncio
async def test_update_user_role_success(admin_service, mock_supabase_admin):
    service, mock_repo = admin_service

    # Setup mocks
    mock_repo.get_user_by_id = AsyncMock(return_value={"id": "user-123", "role": "user"})
    mock_repo.update_user_role = AsyncMock(return_value={"id": "user-123", "role": "admin"})
    
    mock_supabase_admin.auth.admin.update_user_by_id = AsyncMock()

    result = await service.update_user_role("user-123", "admin")

    assert result["role"] == "admin"
    mock_repo.get_user_by_id.assert_called_once_with("user-123")
    mock_supabase_admin.auth.admin.update_user_by_id.assert_called_once_with(
        "user-123", {"app_metadata": {"role": "admin"}}
    )
    mock_repo.update_user_role.assert_called_once_with("user-123", "admin")


@pytest.mark.asyncio
async def test_update_user_role_not_found(admin_service):
    service, mock_repo = admin_service
    mock_repo.get_user_by_id = AsyncMock(return_value=None)

    with pytest.raises(UserNotFoundError):
        await service.update_user_role("nonexistent", "admin")


@pytest.mark.asyncio
async def test_delete_user_success(admin_service, mock_supabase_admin):
    service, mock_repo = admin_service

    mock_repo.get_user_by_id = AsyncMock(return_value={"id": "user-123"})
    mock_supabase_admin.auth.admin.sign_out = AsyncMock()
    mock_supabase_admin.auth.admin.delete_user = AsyncMock()

    await service.delete_user("user-123")

    mock_repo.get_user_by_id.assert_called_once_with("user-123")
    mock_supabase_admin.auth.admin.sign_out.assert_called_once_with("user-123", scope="global")
    mock_supabase_admin.auth.admin.delete_user.assert_called_once_with("user-123")


# ── 3. Admin Repository Unit Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_repository_get_users(mock_supabase):
    repo = AdminRepository(mock_supabase)
    
    mock_execute = MagicMock()
    mock_execute.execute = AsyncMock(return_value=MagicMock(data=[{"id": "u1", "email": "test@test.com"}]))
    
    mock_table = MagicMock()
    mock_table.select = MagicMock(return_value=mock_table)
    mock_table.eq = MagicMock(return_value=mock_table)
    mock_table.order = MagicMock(return_value=mock_table)
    mock_table.range = MagicMock(return_value=mock_execute)
    
    mock_supabase.table.return_value = mock_table

    users = await repo.get_users(role="admin", page=1, limit=10)

    assert len(users) == 1
    assert users[0]["id"] == "u1"
    mock_supabase.table.assert_called_once_with("users")
    mock_table.select.assert_called_once_with("*")
    mock_table.eq.assert_called_once_with("role", "admin")
