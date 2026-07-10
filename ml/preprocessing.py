"""Feature Preprocessing Service.

Handles validation, range checks, and missing value imputation for sensor readings.
"""

from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()

# Safe default values for imputation during cold-starts
DEFAULT_VALUES = {"ph": 7.0, "tds": 250.0, "turbidity": 1.0}

# Physical bounds for validation
VALID_RANGES = {"ph": (0.0, 14.0), "tds": (0.0, 5000.0), "turbidity": (0.0, 5000.0)}


def validate_and_impute_reading(
    reading: Dict[str, Any], history_defaults: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """Validates raw sensor readings and imputes missing or out-of-range values.

    Args:
        reading: Dictionary containing the raw ph, tds, and turbidity values.
        history_defaults: Optional dictionary containing historical averages for imputation.

    Returns:
        A dictionary with validated and imputed float values for ph, tds, and turbidity.
    """
    imputed = {}
    defaults = {**DEFAULT_VALUES, **(history_defaults or {})}

    for feature in ["ph", "tds", "turbidity"]:
        val = reading.get(feature)

        # Check for None, empty, or NaN
        if val is None:
            imputed[feature] = defaults[feature]
            logger.info(
                "preprocessing_missing_value_imputed",
                feature=feature,
                default_value=defaults[feature],
            )
            continue

        try:
            val_float = float(val)
        except (ValueError, TypeError):
            imputed[feature] = defaults[feature]
            logger.warning(
                "preprocessing_invalid_type_imputed",
                feature=feature,
                raw_value=val,
                default_value=defaults[feature],
            )
            continue

        # Range check
        min_val, max_val = VALID_RANGES[feature]
        if min_val <= val_float <= max_val:
            imputed[feature] = val_float
        else:
            imputed[feature] = defaults[feature]
            logger.warning(
                "preprocessing_out_of_range_imputed",
                feature=feature,
                raw_value=val_float,
                default_value=defaults[feature],
            )

    return imputed
