"""Alert Engine.

Contains business rules for alert generation, severity classification,
and user-friendly notification formatting.
"""

from typing import Dict, Any, List
import structlog

logger = structlog.get_logger()


class AlertSeverityClassifier:
    """Classifies alert severity based on sensor thresholds and ML predictions."""

    @staticmethod
    def classify(category: str, value: float, reading: Dict[str, Any]) -> str:
        """Classify severity level ('info', 'warning', 'critical') for an alert."""
        category = category.lower()

        if category == "wqi":
            if value < 65:
                return "critical"
            elif value < 80:
                return "warning"
            return "info"

        elif category == "ph":
            if value < 6.0 or value > 9.0:
                return "critical"
            elif value < 6.5 or value > 8.5:
                return "warning"
            return "info"

        elif category == "tds":
            if value > 600:
                return "critical"
            elif value > 300:
                return "warning"
            return "info"

        elif category == "turbidity":
            if value > 15.0:
                return "critical"
            elif value > 5.0:
                return "warning"
            return "info"

        elif category == "anomaly":
            # Isolation Forest anomalies default to warning severity
            return "warning"

        elif category == "ml_recommendation":
            risk = str(reading.get("risk_level", "low")).lower()
            label = str(reading.get("label", "safe")).lower()
            if risk == "high" or label == "unsafe":
                return "critical"
            elif risk == "medium" or label == "borderline":
                return "warning"
            return "info"

        return "info"


class NotificationFormatter:
    """Formats raw alerts into readable messages and actionable recommendations."""

    @staticmethod
    def format_alert(category: str, severity: str, value: float, reading: Dict[str, Any]) -> Dict[str, str]:
        """Generate user-facing message and recommendation strings."""
        category = category.lower()
        severity = severity.lower()

        message = ""
        recommendation = ""

        if category == "wqi":
            message = f"Poor Water Quality Index (WQI): {value:.1f}"
            if severity == "critical":
                recommendation = "Water quality is unsafe. Avoid ingestion immediately. Boil and filter water for other household activities."
            else:
                recommendation = "Water quality is borderline. Use a carbon filter or boil before drinking."

        elif category == "ph":
            direction = "low (acidic)" if value < 7.0 else "high (alkaline)"
            message = f"pH level deviation: {value:.2f} is {direction}"
            if severity == "critical":
                recommendation = "pH is highly abnormal. This can leach metals or damage plumbing. Avoid drinking and inspect filters/neutralizer."
            else:
                recommendation = "pH is outside the optimal 6.5-8.5 range. Monitor your water treatment system."

        elif category == "tds":
            message = f"Elevated Total Dissolved Solids (TDS): {value:.0f} ppm"
            if severity == "critical":
                recommendation = "TDS is at a critical level. Run water through a Reverse Osmosis (RO) system before consumption."
            else:
                recommendation = "TDS is elevated. Carbon filtration is recommended to improve taste and remove excess minerals."

        elif category == "turbidity":
            message = f"Elevated Turbidity: {value:.1f} NTU"
            if severity == "critical":
                recommendation = "Water contains critical levels of suspended particles. Do not drink. Service sediment filter cartridge immediately."
            else:
                recommendation = "Water is slightly cloudy. Sediment filtration is advised before drinking."

        elif category == "anomaly":
            message = "Unusual water telemetry pattern detected (ML Anomaly)"
            recommendation = "Isolation Forest detected statistical sensor deviance. Inspect sensors for dirt or recalibration, and confirm filter functionality."

        elif category == "ml_recommendation":
            ml_label = str(reading.get("label", "unknown")).upper()
            message = f"ML Classification: Water is predicted to be {ml_label}"
            recommendation = reading.get("recommendation") or "Check filter systems and re-test parameters."

        else:
            message = "Water sensor status update warning"
            recommendation = "Please check your water quality metrics on the dashboard."

        return {
            "message": message,
            "recommendation": recommendation
        }


class AlertRuleEngine:
    """Evaluates telemetry readings and ML outputs against alerting rules."""

    def __init__(self):
        self.severity_classifier = AlertSeverityClassifier()
        self.formatter = NotificationFormatter()

    def evaluate(self, reading: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate a reading and return list of candidate alert payloads.
        
        Note: Alerts are generated only for unsafe or borderline parameters.
        """
        candidates = []
        user_id = reading.get("user_id")
        timestamp = reading.get("timestamp")

        if not user_id:
            return candidates

        # 1. Evaluate WQI
        wqi = reading.get("wqi_score")
        if wqi is not None and wqi < 80.0:
            candidates.append(self._build_candidate("wqi", wqi, reading))

        # 2. Evaluate pH
        ph = reading.get("ph")
        if ph is not None and (ph < 6.5 or ph > 8.5):
            candidates.append(self._build_candidate("ph", ph, reading))

        # 3. Evaluate TDS
        tds = reading.get("tds")
        if tds is not None and tds > 300.0:
            candidates.append(self._build_candidate("tds", tds, reading))

        # 4. Evaluate Turbidity
        turb = reading.get("turbidity")
        if turb is not None and turb > 5.0:
            candidates.append(self._build_candidate("turbidity", turb, reading))

        # 5. Evaluate Isolation Forest Anomaly
        is_anomaly = reading.get("is_anomaly")
        if is_anomaly:
            # Pass anomaly score (usually negative/float value) or 1.0
            score = float(reading.get("anomaly_score", 1.0))
            candidates.append(self._build_candidate("anomaly", score, reading))

        # 6. Evaluate ML Classification label
        label = reading.get("label")
        if label in ("borderline", "unsafe"):
            candidates.append(self._build_candidate("ml_recommendation", 0.0, reading))

        return candidates

    def _build_candidate(self, category: str, value: float, reading: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to classify, format, and construct a candidate alert dictionary."""
        severity = self.severity_classifier.classify(category, value, reading)
        format_info = self.formatter.format_alert(category, severity, value, reading)

        return {
            "user_id": reading.get("user_id"),
            "timestamp": reading.get("timestamp"),
            "category": category,
            "severity": severity,
            "message": format_info["message"],
            "recommendation": format_info["recommendation"],
            "is_read": False,
            "is_acknowledged": False,
            "is_resolved": False
        }
