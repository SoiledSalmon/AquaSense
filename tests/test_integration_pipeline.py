"""Integration tests for the MQTT -> ML Pipeline -> Database -> SSE pipeline."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from app.mqtt_subscriber import handle_mqtt_message
from app.repositories.readings_repository import ReadingsRepository


@pytest.mark.asyncio
async def test_mqtt_ml_db_sse_integration():
    # 1. Arrange Mocks
    # Mock database repository
    repo = MagicMock(spec=ReadingsRepository)
    repo._client = MagicMock()

    mock_inserted_reading = {
        "id": "mock-reading-uuid",
        "user_id": "mock-user-uuid",
        "timestamp": "2026-06-26T23:00:00+00:00",
        "ph": 7.2,
        "tds": 250.0,
        "turbidity": 2.0,
        "wqi_score": None,
        "label": None,
    }

    repo.insert_reading = AsyncMock(return_value=mock_inserted_reading)
    repo.get_recent_readings = AsyncMock(
        return_value=[]
    )  # Empty history for simplicity
    repo.update_reading_ml = AsyncMock(
        return_value={**mock_inserted_reading, "wqi_score": 100.0, "label": "safe"}
    )
    repo.insert_ml_result = AsyncMock()
    repo.create_alert = AsyncMock()

    # Mock SSE Manager
    sse_manager = AsyncMock()

    # Mock MQTT Message
    mqtt_message = MagicMock()
    mqtt_message.topic = "channels/mock-channel-id/subscribe/feeds"
    # Valid normal payload
    payload = {
        "created_at": "2026-06-26T23:00:00Z",
        "field1": "7.2",  # ph
        "field2": "2.0",  # turbidity (Field 2)
        "field3": "250.0",  # tds (Field 3)
    }
    mqtt_message.payload = json.dumps(payload).encode("utf-8")

    # Setup global mapped channel variables in mqtt_subscriber
    from app import mqtt_subscriber

    mqtt_subscriber._channel_to_user_map["mock-channel-id"] = {
        "id": "mock-user-uuid",
        "channel_id": "mock-channel-id",
    }

    # 2. Act
    await handle_mqtt_message(mqtt_message, repo, sse_manager)

    # 3. Assert
    # Verify raw reading was inserted
    repo.insert_reading.assert_called_once()

    # Verify ML pipeline was run and readings table updated with WQI & label
    repo.update_reading_ml.assert_called_once_with("mock-reading-uuid", 100.0, "safe")

    # Verify detailed ML results were written to ml_results
    repo.insert_ml_result.assert_called_once()

    # Verify SSE was triggered for reading_update
    sse_manager.send_event.assert_called_once()
    args = sse_manager.send_event.call_args[0]
    assert args[0] == "mock-user-uuid"
    assert args[1] == "reading_update"
    assert args[2]["wqi_score"] == 100.0
    assert args[2]["label"] == "safe"
    assert args[2]["is_anomaly"] is False
    assert "shap_values" in args[2]


@pytest.mark.asyncio
async def test_mqtt_ml_db_sse_unsafe_triggers_alert():
    # 1. Arrange Mocks
    repo = MagicMock(spec=ReadingsRepository)

    mock_inserted_reading = {
        "id": "mock-reading-uuid-unsafe",
        "user_id": "mock-user-uuid",
        "timestamp": "2026-06-26T23:05:00+00:00",
        "ph": 3.2,  # Acidic (Unsafe)
        "tds": 850.0,  # High TDS (Unsafe)
        "turbidity": 45.0,  # High Turbidity (Unsafe)
        "wqi_score": None,
        "label": None,
    }

    repo.insert_reading = AsyncMock(return_value=mock_inserted_reading)
    repo.get_recent_readings = AsyncMock(return_value=[])
    repo.update_reading_ml = AsyncMock()
    repo.insert_ml_result = AsyncMock()

    repo._client = MagicMock()

    # Mock alert generation response
    mock_created_alert = {
        "id": "mock-alert-uuid",
        "user_id": "mock-user-uuid",
        "timestamp": "2026-06-26T23:05:00+00:00",
        "message": "CRITICAL: Water contains toxic levels...",
        "is_read": False,
        "severity": "critical",
        "category": "ph",
        "is_acknowledged": False,
        "is_resolved": False,
    }

    sse_manager = AsyncMock()

    mqtt_message = MagicMock()
    mqtt_message.topic = "channels/mock-channel-id/subscribe/feeds"
    payload = {
        "created_at": "2026-06-26T23:05:00Z",
        "field1": "3.2",
        "field2": "45.0",  # turbidity (Field 2)
        "field3": "850.0",  # tds (Field 3)
    }
    mqtt_message.payload = json.dumps(payload).encode("utf-8")

    from app import mqtt_subscriber

    mqtt_subscriber._channel_to_user_map["mock-channel-id"] = {
        "id": "mock-user-uuid",
        "channel_id": "mock-channel-id",
    }

    # 2. Act / Assert with patched AlertRepository
    from unittest.mock import patch

    with patch("app.services.alert_service.AlertRepository") as MockAlertRepo:
        mock_alert_repo_inst = MockAlertRepo.return_value
        mock_alert_repo_inst.get_latest_alert_by_category = AsyncMock(return_value=None)
        mock_alert_repo_inst.create_alert = AsyncMock(return_value=mock_created_alert)

        await handle_mqtt_message(mqtt_message, repo, sse_manager)

        # 3. Assert
        # Verify alerts were inserted into DB (one for each of the 6 triggered rules)
        assert mock_alert_repo_inst.create_alert.call_count == 6

    # Verify SSE was triggered for both reading_update and alert_new (compatibility push)
    assert sse_manager.send_event.call_count == 2

    # Check that alert_new event was sent with the correct payload
    calls = sse_manager.send_event.call_args_list
    events = [c[0][1] for c in calls]
    assert "reading_update" in events
    assert "alert_new" in events

    alert_call = [c for c in calls if c[0][1] == "alert_new"][0]
    assert alert_call[0][0] == "mock-user-uuid"
    assert alert_call[0][2]["message"] is not None
