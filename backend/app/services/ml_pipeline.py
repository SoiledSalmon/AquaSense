"""ML Pipeline Orchestrator Service.

Orchestrates preprocessing, feature engineering, WQI calculation,
XGBoost inference, SHAP explanations, Isolation Forest anomaly detection,
and recommendation generation. Handles database persistence and alerts.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
import structlog

from app.repositories.readings_repository import ReadingsRepository
from app.services.alert_service import alert_service
from app.ml import (
    validate_and_impute_reading,
    calculate_wqi,
    compute_ewma_features,
    run_xgb_inference,
    detect_anomaly,
    compute_exact_shap,
    generate_recommendation_and_risk
)

logger = structlog.get_logger()


class MLPipelineService:
    """Orchestrator for the AquaSense three-layer ML pipeline."""

    async def process(self, reading: Dict[str, Any], repo: ReadingsRepository) -> Dict[str, Any]:
        """Runs the ML pipeline for a newly ingested reading.
        
        Args:
            reading: The inserted reading record from the database.
            repo: ReadingsRepository instance for DB access.
            
        Returns:
            The processed reading dict, updated with ML insights and potential alerts.
        """
        reading_id = reading.get("id")
        user_id = reading.get("user_id")
        timestamp_str = reading.get("timestamp")
        
        if not user_id or not reading_id:
            logger.error("ml_pipeline_missing_identifiers", reading_id=reading_id, user_id=user_id)
            return reading

        logger.info("ml_pipeline_execution_started", reading_id=reading_id, user_id=user_id)
        
        # Prepare result copy to modify
        result = {**reading}
        
        try:
            # 1. Input Validation and Imputation
            validated_inputs = validate_and_impute_reading(reading)
            
            # 2. WQI Calculation
            wqi_score = calculate_wqi(
                validated_inputs["ph"],
                validated_inputs["tds"],
                validated_inputs["turbidity"]
            )
            result["wqi_score"] = wqi_score
            
            # 3. EWMA Feature Smoothing
            # Fetch past readings (latest 20) for the user
            history = await repo.get_recent_readings(user_id, limit=20)
            # Remove current reading from history if it is already in the fetched list (avoid double counting)
            history = [h for h in history if h.get("timestamp") != timestamp_str]
            
            smoothed_features = compute_ewma_features(validated_inputs, history)
            
            # 4. XGBoost Inference (on smoothed features)
            label, score, probs = run_xgb_inference(smoothed_features)
            result["label"] = label
            
            # 5. Isolation Forest Anomaly Detection (on smoothed features)
            is_anomaly, anomaly_score = detect_anomaly(smoothed_features)
            
            # 6. SHAP Explanations (for the predicted class)
            shap_values = compute_exact_shap(smoothed_features, label)
            
            # 7. Recommendation and Risk Level Generation
            recommendation, risk_level = generate_recommendation_and_risk(
                validated_inputs,
                label,
                is_anomaly
            )
            
            # Attach ML outputs to result dict (for SSE broadcast)
            result.update({
                "risk_level": risk_level,
                "recommendation": recommendation,
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "shap_values": shap_values,
                **probs
            })
            
            # 8. Persist to Database (with individual try/except to prevent total failure)
            # Update the readings hypertable row
            try:
                await repo.update_reading_ml(reading_id, wqi_score, label)
            except Exception as db_err:
                logger.error("ml_pipeline_readings_update_failed", reading_id=reading_id, error=str(db_err))
                
            # Insert detailed results to ml_results table
            try:
                ml_res_payload = {
                    "reading_id": reading_id,
                    "user_id": user_id,
                    "timestamp": timestamp_str,
                    "ph_smoothed": smoothed_features["ph_smoothed"],
                    "tds_smoothed": smoothed_features["tds_smoothed"],
                    "turb_smoothed": smoothed_features["turb_smoothed"],
                    "anomaly_score": anomaly_score,
                    "is_anomaly": is_anomaly,
                    "shap_ph": shap_values["ph"],
                    "shap_tds": shap_values["tds"],
                    "shap_turbidity": shap_values["turbidity"],
                    "risk_level": risk_level,
                    "recommendation": recommendation
                }
                await repo.insert_ml_result(ml_res_payload)
            except Exception as db_err:
                logger.error("ml_pipeline_ml_results_insert_failed", reading_id=reading_id, error=str(db_err))
                
            # Generate, persist, and publish alerts via AlertService
            try:
                generated_alerts = await alert_service.process_alerts(result, repo._client)
                if generated_alerts:
                    result["new_alert"] = generated_alerts[0]
            except Exception as alert_err:
                logger.error("ml_pipeline_alerts_processing_failed", reading_id=reading_id, error=str(alert_err))
                    
            logger.info("ml_pipeline_execution_success", reading_id=reading_id, label=label, wqi_score=wqi_score)
            
        except Exception as pipeline_err:
            logger.error("ml_pipeline_execution_failed", reading_id=reading_id, error=str(pipeline_err))
            # Fallback to prevent crash: ensure at least basic WQI is estimated if possible
            if "wqi_score" not in result or result["wqi_score"] is None:
                result["wqi_score"] = None
            if "label" not in result or result["label"] is None:
                result["label"] = None

        return result


# Singleton instance
ml_pipeline = MLPipelineService()
