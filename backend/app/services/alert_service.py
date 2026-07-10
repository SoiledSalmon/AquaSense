"""Alert Service.

Orchestrates the evaluation of telemetry, cooldown check against historical alerts,
persistence in the database, and real-time publishing over Server-Sent Events.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
import structlog

from app.repositories.alert_repository import AlertRepository
from app.services.alert_engine import AlertRuleEngine
from app.services.sse_manager import sse_manager

logger = structlog.get_logger()


class AlertPublisher:
    """Publishes alerts to users in real-time over SSE."""

    def __init__(self, sse_mgr=None):
        self._sse_manager = sse_mgr or sse_manager

    async def publish(self, user_id: str, alert: Dict[str, Any]) -> None:
        """Format and send the alert event over SSE."""
        serializable = {}
        for k, v in alert.items():
            if isinstance(v, datetime):
                serializable[k] = v.isoformat()
            else:
                serializable[k] = v
        await self._sse_manager.send_event(user_id, "alert_new", serializable)


class AlertService:
    """Service to evaluate rules, deduplicate, persist, and publish alerts."""

    def __init__(self, publisher: AlertPublisher = None):
        self.engine = AlertRuleEngine()
        self.publisher = publisher or AlertPublisher()

    async def process_alerts(
        self, reading: Dict[str, Any], supabase_client, cooldown_seconds: int = 900
    ) -> List[Dict[str, Any]]:
        """Evaluate reading telemetry, save new alerts to DB, and publish them via SSE.

        Args:
            reading: The telemetry reading dict (including raw values and ML pipeline outputs).
            supabase_client: Supabase client instance.
            cooldown_seconds: Minimum time (in seconds) between alerts of the same category (default 15 minutes).

        Returns:
            List of successfully persisted and published alert dictionaries.
        """
        user_id = reading.get("user_id")
        if not user_id:
            return []

        repo = AlertRepository(supabase_client)
        candidates = self.engine.evaluate(reading)
        generated_alerts = []

        for candidate in candidates:
            category = candidate["category"]
            # Cooldown check: get latest alert of this category to prevent alert fatigue
            try:
                latest = await repo.get_latest_alert_by_category(user_id, category)
                if latest:
                    latest_ts_str = latest.get("timestamp")
                    if latest_ts_str:
                        # Convert ISO format to datetime
                        latest_ts = datetime.fromisoformat(
                            latest_ts_str.replace("Z", "+00:00")
                        )

                        reading_ts_str = reading.get("timestamp")
                        if reading_ts_str:
                            reading_ts = datetime.fromisoformat(
                                reading_ts_str.replace("Z", "+00:00")
                            )
                        else:
                            reading_ts = datetime.now(timezone.utc)

                        # If difference is less than cooldown, suppress alert
                        diff = (reading_ts - latest_ts).total_seconds()
                        if diff < cooldown_seconds:
                            logger.info(
                                "alert_suppressed_cooldown",
                                user_id=user_id,
                                category=category,
                                time_since_last=diff,
                                cooldown=cooldown_seconds,
                            )
                            continue
            except Exception as e:
                logger.warning("alert_cooldown_check_failed", error=str(e))
                # Fall through and create alert anyway on DB error as a fail-safe

            # Persist alert in database
            try:
                alert_record = await repo.create_alert(candidate)
                generated_alerts.append(alert_record)

                # Publish in real-time over SSE
                await self.publisher.publish(user_id, alert_record)
                logger.info(
                    "alert_generated_and_published",
                    alert_id=alert_record.get("id"),
                    category=category,
                )
            except Exception as e:
                logger.error(
                    "alert_creation_or_publish_failed",
                    user_id=user_id,
                    category=category,
                    error=str(e),
                )

        return generated_alerts


# Singleton instance
alert_service = AlertService()
