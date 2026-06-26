"""ML Pipeline Service stub.

Phase 4 will implement this pipeline. Currently, it acts as a stub / passthrough.
"""

import structlog

logger = structlog.get_logger()


class MLPipelineService:
    """Stub service for XGBoost + SHAP + Isolation Forest pipeline."""

    async def process(self, reading: dict) -> dict:
        """Stub process function for incoming readings.
        
        Currently passes the reading through unchanged.
        """
        logger.info("ml_pipeline_stub_called", reading_id=reading.get("id"))
        result = {**reading}
        if "wqi_score" not in result or result["wqi_score"] is None:
            result["wqi_score"] = None
        if "label" not in result or result["label"] is None:
            result["label"] = None
        return result


# Singleton instance
ml_pipeline = MLPipelineService()
