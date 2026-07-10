"""Feature Engineering Service.

Calculates EWMA smoothed sensor values from history to filter noise.
"""

from typing import Dict, Any, List
import pandas as pd
import structlog

logger = structlog.get_logger()


def compute_ewma_features(
    current_reading: Dict[str, float],
    historical_readings: List[Dict[str, Any]],
    span: int = 5,
) -> Dict[str, float]:
    """Calculates EWMA smoothed values for ph, tds, and turbidity.

    Args:
        current_reading: Dictionary of current validated values {"ph": ..., "tds": ..., "turbidity": ...}
        historical_readings: List of past readings (oldest first, chronological order)
        span: Smoothing window span (default: 5, approx alpha = 0.33)

    Returns:
        A dictionary with keys 'ph_smoothed', 'tds_smoothed', and 'turb_smoothed'.
    """
    features = ["ph", "tds", "turbidity"]

    # If no history, return current values as smoothed values
    if not historical_readings:
        return {
            "ph_smoothed": current_reading["ph"],
            "tds_smoothed": current_reading["tds"],
            "turb_smoothed": current_reading["turbidity"],
        }

    # Extract historical feature values (chronological order)
    history_data = []
    for r in historical_readings:
        # Ignore incomplete readings in history
        if all(r.get(f) is not None for f in features):
            history_data.append({f: float(r[f]) for f in features})

    # Append current reading
    history_data.append({f: current_reading[f] for f in features})

    df = pd.DataFrame(history_data)

    # Apply Exponentially Weighted Moving Average
    # ewm() computes EWMA: y_t = (1 - alpha)*y_{t-1} + alpha*x_t
    ewma_df = df.ewm(span=span, adjust=False).mean()

    # Get the latest row (current smoothed values)
    latest_smoothed = ewma_df.iloc[-1]

    smoothed = {
        "ph_smoothed": float(latest_smoothed["ph"]),
        "tds_smoothed": float(latest_smoothed["tds"]),
        "turb_smoothed": float(latest_smoothed["turbidity"]),
    }

    logger.debug(
        "ewma_smoothing_completed",
        raw=current_reading,
        smoothed=smoothed,
        history_count=len(historical_readings),
    )

    return smoothed
