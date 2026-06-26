"""Tests for the updated liveness health check API endpoint."""

from fastapi.testclient import TestClient
from app.main import app

def test_health_check_endpoint():
    """Verify that the health check endpoint returns status, service name, and MQTT status."""
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "backend"
        # Since the background tasks are started during lifespan inside the TestClient context,
        # app.state.mqtt_status should be initialized (usually "starting", "connected", "stopped", etc.)
        assert "mqtt_status" in data
        assert data["mqtt_status"] in ("starting", "connected", "reconnecting", "stopped", "error", "unknown")
