"""Isolation Forest Anomaly Detection Service.

Uses the trained Isolation Forest model to flag abnormal sensor values.
"""

from typing import Dict, Tuple
import pandas as pd
import structlog
from app.ml.loader import get_iforest_model

logger = structlog.get_logger()


def detect_anomaly(features: Dict[str, float]) -> Tuple[bool, float]:
    """Runs anomaly detection on features using Isolation Forest.
    
    Args:
        features: Dictionary containing {"ph": ..., "tds": ..., "turbidity": ...}
        
    Returns:
        A tuple containing:
          - A boolean: True if the reading is flagged as an anomaly, False otherwise
          - The decision score: higher scores represent normal data, lower scores represent anomalies
    """
    model = get_iforest_model()
    
    # Ensure features have correct names for the model
    model_features = {
        "ph": features.get("ph_smoothed", features.get("ph")),
        "tds": features.get("tds_smoothed", features.get("tds")),
        "turbidity": features.get("turb_smoothed", features.get("turbidity"))
    }
    input_df = pd.DataFrame([model_features])
    
    # decision_function: average anomaly score. 
    # Values close to 0 or negative are anomalies, positive are normal.
    score = float(model.decision_function(input_df)[0])
    
    # predict returns 1 for inliers (normal) and -1 for outliers (anomalies)
    prediction = int(model.predict(input_df)[0])
    is_anomaly = (prediction == -1)
    
    logger.debug(
        "anomaly_detection_completed",
        is_anomaly=is_anomaly,
        anomaly_score=score
    )
    
    return is_anomaly, score
