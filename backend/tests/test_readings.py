"""Tests for the Readings API router and SSEManager."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from app.main import app
from app.core.dependencies import get_current_user
from app.api.readings_router import _get_readings_repo
from app.services.sse_manager import SSEManager


# ── 1. SSEManager Unit Tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_sse_manager_lifecycle():
    manager = SSEManager()
    user_id = "test-user-uuid"

    # Connect client 1
    q1 = await manager.connect(user_id)
    assert user_id in manager._user_queues
    assert len(manager._user_queues[user_id]) == 1

    # Connect client 2 (same user, e.g. second tab)
    q2 = await manager.connect(user_id)
    assert len(manager._user_queues[user_id]) == 2

    # Broadcast event
    test_data = {"ph": 7.0, "tds": 200.0}
    await manager.send_event(user_id, "reading_update", test_data)

    # Verify both queues received the payload
    event1 = await q1.get()
    event2 = await q2.get()

    assert event1["event"] == "reading_update"
    assert event1["data"] == test_data
    assert event2["event"] == "reading_update"
    assert event2["data"] == test_data

    # Disconnect client 1
    await manager.disconnect(user_id, q1)
    assert len(manager._user_queues[user_id]) == 1

    # Disconnect client 2
    await manager.disconnect(user_id, q2)
    assert user_id not in manager._user_queues


# ── 2. Readings API Router Tests ──────────────────────────────────────

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_latest_reading = AsyncMock()
    repo.get_hourly_readings = AsyncMock()
    repo.get_daily_readings = AsyncMock()
    return repo


@pytest.fixture
def client(mock_repo):
    # Override authentication dependency to return a mock user profile
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": "mock-user-uuid-123",
        "email": "test@example.com",
        "role": "user"
    }
    # Override repository dependency to inject our mock repo
    app.dependency_overrides[_get_readings_repo] = lambda: mock_repo

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides after test runs
    app.dependency_overrides.clear()


def test_get_latest_reading_success(client, mock_repo):
    mock_reading = {
        "timestamp": "2026-06-26T22:00:00+00:00",
        "id": "reading-uuid-1",
        "user_id": "mock-user-uuid-123",
        "ph": 7.2,
        "tds": 250.0,
        "turbidity": 15.0,
        "wqi_score": 85.0,
        "label": "safe"
    }
    mock_repo.get_latest_reading.return_value = mock_reading

    response = client.get("/api/readings/latest")
    assert response.status_code == 200
    assert response.json() == {"reading": mock_reading}
    mock_repo.get_latest_reading.assert_called_once_with("mock-user-uuid-123")


def test_get_latest_reading_not_found(client, mock_repo):
    mock_repo.get_latest_reading.return_value = None

    response = client.get("/api/readings/latest")
    assert response.status_code == 200
    assert response.json() == {"reading": None}
    mock_repo.get_latest_reading.assert_called_once_with("mock-user-uuid-123")


def test_get_readings_history_24h(client, mock_repo):
    mock_data = [
        {"bucket": "2026-06-26T21:00:00+00:00", "avg_ph": 7.1, "avg_tds": 240.0, "avg_turbidity": 14.0, "avg_wqi": 84.0}
    ]
    mock_repo.get_hourly_readings.return_value = mock_data

    response = client.get("/api/readings?range=24h")
    assert response.status_code == 200
    assert response.json() == {"range": "24h", "data": mock_data}
    mock_repo.get_hourly_readings.assert_called_once_with("mock-user-uuid-123", limit=24)


def test_get_readings_history_7d(client, mock_repo):
    mock_data = [
        {"bucket": "2026-06-26T00:00:00+00:00", "avg_ph": 7.3, "avg_tds": 245.0, "avg_turbidity": 14.5, "avg_wqi": 86.0}
    ]
    mock_repo.get_daily_readings.return_value = mock_data

    response = client.get("/api/readings?range=7d")
    assert response.status_code == 200
    assert response.json() == {"range": "7d", "data": mock_data}
    mock_repo.get_daily_readings.assert_called_once_with("mock-user-uuid-123", limit=7)


def test_get_readings_history_invalid_range(client):
    response = client.get("/api/readings?range=invalid")
    assert response.status_code == 422  # Pydantic query param validation failure status code
