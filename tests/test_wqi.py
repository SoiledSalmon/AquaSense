"""Unit tests for WQI calculations."""

from ml.wqi import calculate_wqi


def test_calculate_wqi_excellent():
    # Optimal values should yield WQI close to 100
    wqi = calculate_wqi(ph=7.2, tds=150.0, turbidity=1.0)
    assert wqi >= 95.0
    assert wqi <= 100.0


def test_calculate_wqi_good():
    # Slightly elevated values should yield a good score (80 to 95)
    wqi = calculate_wqi(ph=7.2, tds=450.0, turbidity=10.0)
    assert 80.0 <= wqi < 95.0


def test_calculate_wqi_fair():
    # Moderately elevated values should yield a fair score (65 to 80)
    wqi = calculate_wqi(ph=5.0, tds=800.0, turbidity=30.0)
    assert 65.0 <= wqi < 80.0


def test_calculate_wqi_unsafe():
    # Extremely abnormal values should yield an unsafe score
    wqi = calculate_wqi(ph=4.5, tds=1200.0, turbidity=35.0)
    assert wqi < 65.0
    assert wqi >= 0.0
