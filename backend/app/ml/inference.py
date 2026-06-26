"""XGBoost Inference Service.

Uses the trained XGBoost model to classify water quality into risk classes.
"""

from typing import Dict, Tuple
import pandas as pd
import numpy as np
import structlog
from app.ml.loader import get_xgb_model

logger = structlog.get_logger()

# Label mapping
CLASS_LABELS = {
    0: "safe",
    1: "borderline",
    2: "unsafe"
}


def run_xgb_inference(features: Dict[str, float]) -> Tuple[str, float, Dict[str, float]]:
    """Runs inference on features using the XGBoost model.
    
    Args:
        features: Dictionary containing {"ph": ..., "tds": ..., "turbidity": ...}
        
    Returns:
        A tuple containing:
          - The predicted label: 'safe', 'borderline', or 'unsafe'
          - The probability score for the predicted class
          - A dictionary of probabilities for all classes
    """
    model = get_xgb_model()
    
    # Ensure features have correct names for the model
    model_features = {
        "ph": features.get("ph_smoothed", features.get("ph")),
        "tds": features.get("tds_smoothed", features.get("tds")),
        "turbidity": features.get("turb_smoothed", features.get("turbidity"))
    }
    input_df = pd.DataFrame([model_features])
    
    # Predict probabilities
    # Scikit-learn API: predict_proba returns [num_samples, num_classes]
    probs = model.predict_proba(input_df)[0]
    
    # Find the class with the highest probability
    pred_class_idx = int(np.argmax(probs))
    pred_label = CLASS_LABELS[pred_class_idx]
    pred_prob = float(probs[pred_class_idx])
    
    # Format all class probabilities
    probabilities = {
        "safe_probability": float(probs[0]),
        "borderline_probability": float(probs[1]),
        "unsafe_probability": float(probs[2])
    }
    
    logger.debug(
        "xgb_inference_completed",
        predicted_label=pred_label,
        probability=pred_prob,
        all_probs=probabilities
    )
    
    return pred_label, pred_prob, probabilities
