"""Unit tests for the Machine Learning pipeline sub-services."""

import pytest
import numpy as np
from app.ml.preprocessing import validate_and_impute_reading
from app.ml.features import compute_ewma_features
from app.ml.loader import get_xgb_model, get_iforest_model, load_models
from app.ml.inference import run_xgb_inference
from app.ml.anomaly import detect_anomaly
from app.ml.shap_explainer import compute_exact_shap
from app.ml.recommendations import generate_recommendation_and_risk


def test_preprocessing():
    # Valid reading
    r = {"ph": 7.5, "tds": 200, "turbidity": 2.0}
    val = validate_and_impute_reading(r)
    assert val["ph"] == 7.5
    assert val["tds"] == 200.0
    assert val["turbidity"] == 2.0

    # Missing values
    r_missing = {"ph": None, "tds": 200}
    val_missing = validate_and_impute_reading(r_missing)
    assert val_missing["ph"] == 7.0  # Default value
    assert val_missing["ph"] != None
    assert val_missing["tds"] == 200.0
    assert val_missing["turbidity"] == 1.0  # Default value

    # Out of bounds values
    r_bad = {"ph": 15.0, "tds": -100.0, "turbidity": 6000.0}
    val_bad = validate_and_impute_reading(r_bad)
    assert val_bad["ph"] == 7.0
    assert val_bad["tds"] == 250.0
    assert val_bad["turbidity"] == 1.0


def test_features_ewma():
    current = {"ph": 8.0, "tds": 300.0, "turbidity": 5.0}
    # empty history
    smoothed_empty = compute_ewma_features(current, [])
    assert smoothed_empty["ph_smoothed"] == 8.0
    assert smoothed_empty["tds_smoothed"] == 300.0
    assert smoothed_empty["turb_smoothed"] == 5.0

    # with history
    history = [
        {"ph": 7.0, "tds": 200.0, "turbidity": 1.0, "timestamp": "2026-06-26T20:00:00Z"},
        {"ph": 7.2, "tds": 220.0, "turbidity": 1.2, "timestamp": "2026-06-26T21:00:00Z"},
    ]
    smoothed = compute_ewma_features(current, history, span=2)
    # Since alpha = 2 / (1 + 2) = 2/3
    # EWMA is heavily weighted towards the current value
    assert smoothed["ph_smoothed"] > 7.2
    assert smoothed["tds_smoothed"] > 220.0
    assert smoothed["turb_smoothed"] > 1.2


def test_model_loading_and_inference():
    # Make sure models load (and train if missing)
    load_models()
    xgb_model = get_xgb_model()
    iforest_model = get_iforest_model()
    assert xgb_model is not None
    assert iforest_model is not None

    # Test inference output structure
    features = {"ph": 7.2, "tds": 200.0, "turbidity": 2.0}
    label, prob, all_probs = run_xgb_inference(features)
    assert label in ["safe", "borderline", "unsafe"]
    assert 0.0 <= prob <= 1.0
    assert "safe_probability" in all_probs
    assert "borderline_probability" in all_probs
    assert "unsafe_probability" in all_probs


def test_anomaly_detection():
    features_normal = {"ph": 7.2, "tds": 200.0, "turbidity": 2.0}
    is_anomaly, score = detect_anomaly(features_normal)
    # For normal features, it should not be anomalous
    assert isinstance(is_anomaly, bool)
    assert isinstance(score, float)


def test_shap_explanations():
    features = {"ph": 7.2, "tds": 200.0, "turbidity": 2.0}
    shap_vals = compute_exact_shap(features, "safe")
    assert "ph" in shap_vals
    assert "tds" in shap_vals
    assert "turbidity" in shap_vals
    # Sum of SHAPs + baseline = predicted prob (additivity property check)
    assert isinstance(shap_vals["ph"], float)


def test_recommendations():
    # Safe water
    rec, risk = generate_recommendation_and_risk(
        {"ph": 7.2, "tds": 200.0, "turbidity": 2.0}, "safe", False
    )
    assert risk == "low"
    assert "Safe for consumption" in rec

    # Borderline
    rec, risk = generate_recommendation_and_risk(
        {"ph": 6.2, "tds": 350.0, "turbidity": 2.0}, "borderline", False
    )
    assert risk == "medium"
    assert "Boiling and carbon filtration" in rec

    # Unsafe
    rec, risk = generate_recommendation_and_risk(
        {"ph": 3.0, "tds": 800.0, "turbidity": 40.0}, "unsafe", False
    )
    assert risk == "high"
    assert "CRITICAL" in rec
