"""Recommendation Engine Service.

Generates contextual, plain-language recommendations and risk levels based on sensor inputs.
"""

from typing import Dict, Tuple
import structlog

logger = structlog.get_logger()


def generate_recommendation_and_risk(
    features: Dict[str, float], predicted_label: str, is_anomaly: bool
) -> Tuple[str, str]:
    """Generates plain-language recommendation text and risk level.

    Args:
        features: Dictionary of sensor values {"ph": ..., "tds": ..., "turbidity": ...}
        predicted_label: The predicted classification label: 'safe', 'borderline', or 'unsafe'
        is_anomaly: Anomaly status from Isolation Forest

    Returns:
        A tuple of (recommendation_text, risk_level)
          - risk_level: 'low', 'medium', or 'high'
          - recommendation_text: Plain-language instructions for the user
    """
    ph = features.get("ph", 7.0)
    tds = features.get("tds", 250.0)
    turbidity = features.get("turbidity", 1.0)

    # 1. Evaluate specific issues
    issues = []
    critical_issues = []

    # pH evaluation
    if ph < 6.5 or ph > 8.5:
        issues.append(f"abnormal pH ({ph:.2f})")
    if ph < 6.0 or ph > 9.0:
        critical_issues.append(f"highly acidic/alkaline pH of {ph:.2f}")

    # TDS evaluation
    if tds > 300.0:
        issues.append(f"elevated TDS ({int(tds)} ppm)")
    if tds > 600.0:
        critical_issues.append(f"critical TDS of {int(tds)} ppm")

    # Turbidity evaluation
    if turbidity > 5.0:
        issues.append(f"raised turbidity ({turbidity:.2f} NTU)")
    if turbidity > 15.0:
        critical_issues.append(f"extreme turbidity of {turbidity:.2f} NTU")

    # 2. Map label and anomaly status to recommendation and risk level
    if predicted_label == "unsafe" or is_anomaly or critical_issues:
        risk_level = "high"
        if critical_issues:
            desc = " and ".join(critical_issues)
        elif issues:
            desc = "Elevated contaminants: " + ", ".join(issues)
        else:
            desc = "unusual statistical readings (anomaly detected)"
        recommendation = f"CRITICAL: Water contains toxic levels of {desc}. Do not consume. Service your active filtration membrane immediately."

    elif predicted_label == "borderline" or issues:
        risk_level = "medium"
        desc = ", ".join(issues) if issues else "minor sensor deviations"
        recommendation = f"Water is borderline safe due to {desc}. Boiling and carbon filtration are recommended before consumption."

    else:
        risk_level = "low"
        recommendation = "Water parameters reside in the optimal range. Safe for consumption, hygiene, and general household usage."

    logger.debug(
        "recommendation_generated",
        predicted_label=predicted_label,
        is_anomaly=is_anomaly,
        risk_level=risk_level,
        recommendation=recommendation,
    )

    return recommendation, risk_level
