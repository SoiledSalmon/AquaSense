"""Unit tests for Phase 5 Alerting Subsystem.

Tests AlertSeverityClassifier, NotificationFormatter, AlertRuleEngine,
and AlertService cooldown/deduplication logic.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.alert_engine import (
    AlertSeverityClassifier,
    NotificationFormatter,
    AlertRuleEngine,
)
from app.services.alert_service import AlertService, AlertPublisher
from app.repositories.alert_repository import AlertRepository


def test_severity_classification():
    # 1. WQI classification
    assert AlertSeverityClassifier.classify("wqi", 50.0, {}) == "critical"
    assert AlertSeverityClassifier.classify("wqi", 70.0, {}) == "warning"
    assert AlertSeverityClassifier.classify("wqi", 90.0, {}) == "info"

    # 2. pH classification
    assert AlertSeverityClassifier.classify("ph", 3.0, {}) == "critical"
    assert AlertSeverityClassifier.classify("ph", 6.2, {}) == "warning"
    assert AlertSeverityClassifier.classify("ph", 7.0, {}) == "info"
    assert AlertSeverityClassifier.classify("ph", 8.8, {}) == "warning"
    assert AlertSeverityClassifier.classify("ph", 10.5, {}) == "critical"

    # 3. TDS classification
    assert AlertSeverityClassifier.classify("tds", 800.0, {}) == "critical"
    assert AlertSeverityClassifier.classify("tds", 450.0, {}) == "warning"
    assert AlertSeverityClassifier.classify("tds", 150.0, {}) == "info"

    # 4. Turbidity classification
    assert AlertSeverityClassifier.classify("turbidity", 20.0, {}) == "critical"
    assert AlertSeverityClassifier.classify("turbidity", 8.0, {}) == "warning"
    assert AlertSeverityClassifier.classify("turbidity", 2.0, {}) == "info"

    # 5. Anomaly classification
    assert AlertSeverityClassifier.classify("anomaly", 0.5, {}) == "warning"

    # 6. ML Recommendation classification
    assert (
        AlertSeverityClassifier.classify(
            "ml_recommendation", 0.0, {"risk_level": "high", "label": "unsafe"}
        )
        == "critical"
    )
    assert (
        AlertSeverityClassifier.classify(
            "ml_recommendation", 0.0, {"risk_level": "medium", "label": "borderline"}
        )
        == "warning"
    )
    assert (
        AlertSeverityClassifier.classify(
            "ml_recommendation", 0.0, {"risk_level": "low", "label": "safe"}
        )
        == "info"
    )


def test_notification_formatting():
    # WQI Critical formatting
    wqi_crit = NotificationFormatter.format_alert("wqi", "critical", 55.0, {})
    assert "Poor Water Quality" in wqi_crit["message"]
    assert "unsafe" in wqi_crit["recommendation"]

    # pH Warning formatting
    ph_warn = NotificationFormatter.format_alert("ph", "warning", 6.2, {})
    assert "pH level deviation" in ph_warn["message"]
    assert "acidic" in ph_warn["message"]
    assert "6.5-8.5" in ph_warn["recommendation"]

    # TDS Critical formatting
    tds_crit = NotificationFormatter.format_alert("tds", "critical", 750.0, {})
    assert "TDS" in tds_crit["message"]
    assert "Reverse Osmosis" in tds_crit["recommendation"]

    # Anomaly formatting
    anomaly_warn = NotificationFormatter.format_alert("anomaly", "warning", -0.15, {})
    assert "Unusual water telemetry" in anomaly_warn["message"]
    assert "Isolation Forest" in anomaly_warn["recommendation"]


def test_rule_engine_evaluation():
    engine = AlertRuleEngine()

    # Normal reading (should generate no candidate alerts)
    normal_reading = {
        "user_id": "user-uuid-1",
        "timestamp": "2026-06-26T23:00:00Z",
        "ph": 7.2,
        "tds": 150.0,
        "turbidity": 2.0,
        "wqi_score": 92.5,
        "is_anomaly": False,
        "label": "safe",
        "risk_level": "low",
    }
    candidates = engine.evaluate(normal_reading)
    assert len(candidates) == 0

    # Critical / Warning reading (should generate multiple candidate alerts)
    bad_reading = {
        "user_id": "user-uuid-1",
        "timestamp": "2026-06-26T23:00:00Z",
        "ph": 3.5,  # ph deviation
        "tds": 800.0,  # tds deviation
        "turbidity": 22.0,  # turbidity deviation
        "wqi_score": 45.0,  # wqi deviation
        "is_anomaly": True,  # anomaly
        "label": "unsafe",  # ml classification
        "risk_level": "high",
    }
    candidates = engine.evaluate(bad_reading)
    # Checks that we generated alerts for wqi, ph, tds, turbidity, anomaly, ml_recommendation
    assert len(candidates) == 6
    categories = [c["category"] for c in candidates]
    assert "wqi" in categories
    assert "ph" in categories
    assert "tds" in categories
    assert "turbidity" in categories
    assert "anomaly" in categories
    assert "ml_recommendation" in categories

    # Verify candidate properties
    wqi_candidate = [c for c in candidates if c["category"] == "wqi"][0]
    assert wqi_candidate["severity"] == "critical"
    assert wqi_candidate["is_read"] is False
    assert wqi_candidate["is_acknowledged"] is False


@pytest.mark.asyncio
async def test_alert_service_cooldown_deduplication():
    # Setup mock publisher
    mock_publisher = AsyncMock(spec=AlertPublisher)
    service = AlertService(publisher=mock_publisher)

    # Mock client and repository
    mock_client = MagicMock()
    MagicMock(spec=AlertRepository)

    # Use patch-like mock creation for repository instantiation inside AlertService
    original_repo_init = AlertRepository.__init__
    AlertRepository.__init__ = lambda self, client: setattr(self, "_client", client)

    # Bind mocks to AlertRepository methods
    AlertRepository.create_alert = AsyncMock(
        return_value={"id": "new-alert-uuid", "category": "ph"}
    )

    try:
        # Scenario A: No previous alert of this category (should create new alert)
        AlertRepository.get_latest_alert_by_category = AsyncMock(return_value=None)

        reading = {
            "user_id": "user-uuid-1",
            "timestamp": "2026-06-26T23:00:00Z",
            "ph": 3.0,
            "tds": 150.0,
            "turbidity": 2.0,
            "wqi_score": 90.0,
        }

        alerts = await service.process_alerts(
            reading, mock_client, cooldown_seconds=600
        )
        assert len(alerts) == 1
        assert alerts[0]["id"] == "new-alert-uuid"
        mock_publisher.publish.assert_called_once()

        # Scenario B: Previous alert exists within cooldown (should be suppressed)
        mock_publisher.publish.reset_mock()
        AlertRepository.create_alert.reset_mock()

        # Previous alert triggered 5 mins ago (300s), cooldown is 10 mins (600s)
        previous_alert = {
            "id": "prev-alert-uuid",
            "timestamp": "2026-06-26T22:55:00Z",
            "category": "ph",
        }
        AlertRepository.get_latest_alert_by_category = AsyncMock(
            return_value=previous_alert
        )

        alerts_suppressed = await service.process_alerts(
            reading, mock_client, cooldown_seconds=600
        )
        assert len(alerts_suppressed) == 0
        AlertRepository.create_alert.assert_not_called()
        mock_publisher.publish.assert_not_called()

        # Scenario C: Previous alert exists outside cooldown (should create new alert)
        # Previous alert triggered 12 mins ago (720s), cooldown is 10 mins (600s)
        previous_alert_old = {
            "id": "prev-alert-uuid-old",
            "timestamp": "2026-06-26T22:48:00Z",
            "category": "ph",
        }
        AlertRepository.get_latest_alert_by_category = AsyncMock(
            return_value=previous_alert_old
        )

        alerts_new = await service.process_alerts(
            reading, mock_client, cooldown_seconds=600
        )
        assert len(alerts_new) == 1
        assert alerts_new[0]["id"] == "new-alert-uuid"

    finally:
        # Restore original repository constructor to avoid side effects in other tests
        AlertRepository.__init__ = original_repo_init
