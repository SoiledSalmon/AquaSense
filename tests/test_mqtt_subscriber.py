"""Tests for the MQTT Subscriber parsing and validation logic."""

from datetime import datetime, timezone
import pytest
from app.mqtt_subscriber import parse_float, ReadingInsert


def test_parse_float():
    assert parse_float("7.2") == 7.2
    assert parse_float(" 1234.56 ") == 1234.56
    assert parse_float(None) is None
    assert parse_float("NaN") is None
    assert parse_float("None") is None
    assert parse_float("") is None
    assert parse_float("invalid") is None


def test_reading_insert_validation():
    # Valid model
    ts = datetime.now(timezone.utc)
    reading = ReadingInsert(
        timestamp=ts,
        user_id="e223d6a0-43f0-466d-8a03-7cf5d5069273",
        ph=7.2,
        tds=450.5,
        turbidity=12.3,
    )
    assert reading.ph == 7.2
    assert reading.tds == 450.5
    assert reading.turbidity == 12.3

    # Invalid range: pH too high
    with pytest.raises(ValueError):
        ReadingInsert(
            timestamp=ts, user_id="e223d6a0-43f0-466d-8a03-7cf5d5069273", ph=14.5
        )

    # Invalid range: pH negative
    with pytest.raises(ValueError):
        ReadingInsert(
            timestamp=ts, user_id="e223d6a0-43f0-466d-8a03-7cf5d5069273", ph=-0.5
        )

    # Invalid range: tds negative
    with pytest.raises(ValueError):
        ReadingInsert(
            timestamp=ts, user_id="e223d6a0-43f0-466d-8a03-7cf5d5069273", tds=-10.0
        )
