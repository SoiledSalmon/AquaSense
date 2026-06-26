"""SHAP Explanation Service.

Computes mathematically exact SHAP values for XGBoost model predictions.
Bypasses native package compilation dependencies to ensure 100% compatibility.
"""

from typing import Dict, List, Any
import pandas as pd
import structlog
from app.ml.loader import get_xgb_model

logger = structlog.get_logger()

# Default baseline / background values representing optimal water quality
DEFAULT_BASELINE = {
    "ph": 7.0,
    "tds": 250.0,
    "turbidity": 1.0
}

LABEL_TO_IDX = {
    "safe": 0,
    "borderline": 1,
    "unsafe": 2
}


def evaluate_coalition(
    S: List[str],
    features: Dict[str, float],
    baseline: Dict[str, float],
    model,
    class_idx: int
) -> float:
    """Evaluates the model prediction for a specific coalition subset of features."""
    query = {}
    for key in ["ph", "tds", "turbidity"]:
        if key in S:
            query[key] = features[key]
        else:
            query[key] = baseline[key]
            
    query_df = pd.DataFrame([query])
    probs = model.predict_proba(query_df)[0]
    return float(probs[class_idx])


def compute_exact_shap(
    features: Dict[str, float],
    predicted_label: str,
    baseline: Dict[str, float] = None
) -> Dict[str, float]:
    """Computes exact SHAP values for the predicted class.
    
    Uses the marginal contribution formula across all coalitions.
    Since we have exactly 3 features (ph, tds, turbidity), 
    we evaluate the 2^3 = 8 possible coalitions.
    
    Args:
        features: Dictionary containing {"ph": ..., "tds": ..., "turbidity": ...}
        predicted_label: The predicted class ('safe', 'borderline', or 'unsafe')
        baseline: Optional baseline/background feature values
        
    Returns:
        A dictionary mapping each feature name to its SHAP value.
    """
    model = get_xgb_model()
    class_idx = LABEL_TO_IDX.get(predicted_label, 0)
    bg = baseline or DEFAULT_BASELINE
    
    # Map smoothed keys to raw feature keys if necessary
    model_features = {
        "ph": features.get("ph_smoothed", features.get("ph")),
        "tds": features.get("tds_smoothed", features.get("tds")),
        "turbidity": features.get("turb_smoothed", features.get("turbidity"))
    }
    
    # Pre-evaluate the 8 possible coalitions
    # Empty subset
    f_empty = evaluate_coalition([], model_features, bg, model, class_idx)
    # Singletons
    f_ph = evaluate_coalition(["ph"], model_features, bg, model, class_idx)
    f_tds = evaluate_coalition(["tds"], model_features, bg, model, class_idx)
    f_turb = evaluate_coalition(["turbidity"], model_features, bg, model, class_idx)
    # Pairs
    f_ph_tds = evaluate_coalition(["ph", "tds"], model_features, bg, model, class_idx)
    f_ph_turb = evaluate_coalition(["ph", "turbidity"], model_features, bg, model, class_idx)
    f_tds_turb = evaluate_coalition(["tds", "turbidity"], model_features, bg, model, class_idx)
    # Full set
    f_all = evaluate_coalition(["ph", "tds", "turbidity"], model_features, bg, model, class_idx)
    
    # Calculate SHAP value for pH
    # Subsets not containing pH: {}, {tds}, {turbidity}, {tds, turbidity}
    shap_ph = (
        (1.0 / 3.0) * (f_ph - f_empty) +
        (1.0 / 6.0) * (f_ph_tds - f_tds) +
        (1.0 / 6.0) * (f_ph_turb - f_turb) +
        (1.0 / 3.0) * (f_all - f_tds_turb)
    )
    
    # Calculate SHAP value for TDS
    # Subsets not containing TDS: {}, {ph}, {turbidity}, {ph, turbidity}
    shap_tds = (
        (1.0 / 3.0) * (f_tds - f_empty) +
        (1.0 / 6.0) * (f_ph_tds - f_ph) +
        (1.0 / 6.0) * (f_tds_turb - f_turb) +
        (1.0 / 3.0) * (f_all - f_ph_turb)
    )
    
    # Calculate SHAP value for Turbidity
    # Subsets not containing Turbidity: {}, {ph}, {tds}, {ph, tds}
    shap_turb = (
        (1.0 / 3.0) * (f_turb - f_empty) +
        (1.0 / 6.0) * (f_ph_turb - f_ph) +
        (1.0 / 6.0) * (f_tds_turb - f_tds) +
        (1.0 / 3.0) * (f_all - f_ph_tds)
    )
    
    shap_values = {
        "ph": round(shap_ph, 4),
        "tds": round(shap_tds, 4),
        "turbidity": round(shap_turb, 4)
    }
    
    logger.debug(
        "shap_values_computed",
        predicted_label=predicted_label,
        shap_values=shap_values,
        base_value=f_empty,
        predicted_value=f_all,
        sum_check=round(f_empty + shap_ph + shap_tds + shap_turb, 4)
    )
    
    return shap_values
