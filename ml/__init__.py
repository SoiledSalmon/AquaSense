"""AquaSense Machine Learning Engine.

Exposes primary preprocessing, WQI calculation, inference, SHAP explanation,
anomaly detection, and recommendation generation functions.
"""

from .preprocessing import validate_and_impute_reading
from .wqi import calculate_wqi
from .features import compute_ewma_features
from .loader import load_models, get_xgb_model, get_iforest_model
from .inference import run_xgb_inference
from .anomaly import detect_anomaly
from .shap_explainer import compute_exact_shap
from .recommendations import generate_recommendation_and_risk

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
