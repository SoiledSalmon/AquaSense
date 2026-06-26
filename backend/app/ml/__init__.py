"""AquaSense Machine Learning Engine.

Exposes primary preprocessing, WQI calculation, inference, SHAP explanation,
anomaly detection, and recommendation generation functions.
"""

from app.ml.preprocessing import validate_and_impute_reading
from app.ml.wqi import calculate_wqi
from app.ml.features import compute_ewma_features
from app.ml.loader import load_models, get_xgb_model, get_iforest_model
from app.ml.inference import run_xgb_inference
from app.ml.anomaly import detect_anomaly
from app.ml.shap_explainer import compute_exact_shap
from app.ml.recommendations import generate_recommendation_and_risk

__all__ = [
    "validate_and_impute_reading",
    "calculate_wqi",
    "compute_ewma_features",
    "load_models",
    "get_xgb_model",
    "get_iforest_model",
    "run_xgb_inference",
    "detect_anomaly",
    "compute_exact_shap",
    "generate_recommendation_and_risk",
]
