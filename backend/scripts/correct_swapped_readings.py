import os
import sys
import asyncio
import structlog

# Add backend and repository root directories to path dynamically
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
sys.path.append(os.path.join(root_dir, "backend"))
sys.path.append(root_dir)

from supabase import create_async_client
from app.core.config import get_settings
from app.repositories.readings_repository import ReadingsRepository
from app.repositories.alert_repository import AlertRepository
from ml import (
    load_models,
    validate_and_impute_reading,
    calculate_wqi,
    compute_ewma_features,
    run_xgb_inference,
    detect_anomaly,
    compute_exact_shap,
    generate_recommendation_and_risk,
)
from app.services.alert_service import alert_service

logger = structlog.get_logger()


async def correct_readings_for_user(client, user_id: str):
    repo = ReadingsRepository(client)
    AlertRepository(client)

    # 1. Fetch all readings for this user in chronological order
    res = (
        await client.table("readings")
        .select("*")
        .eq("user_id", user_id)
        .order("timestamp", desc=False)
        .execute()
    )
    readings = res.data or []
    print(f"Found {len(readings)} readings to correct for user {user_id}")

    if not readings:
        return

    # 2. Delete all existing alerts and ML results for this user to avoid duplicates/stale data
    # (Since we are re-processing every reading chronologically, we will regenerate them perfectly)
    print("Deleting existing alerts and ML results...")
    await client.table("ml_results").delete().eq("user_id", user_id).execute()
    await client.table("alerts").delete().eq("user_id", user_id).execute()

    # Reset alert engine internal state / mock publisher to prevent actual SSE connection tries in script
    # (Since alert publisher tries to use the global sse_manager, we can mock it to just print/ignore during script execution)
    from app.services.alert_service import alert_service as service_instance

    service_instance.publisher.publish = lambda uid, alert: asyncio.sleep(0)  # No-op

    corrected_count = 0

    # 3. Process each reading in chronological order
    for idx, reading in enumerate(readings):
        reading_id = reading["id"]
        timestamp_str = reading["timestamp"]

        # Swap tds and turbidity values
        old_tds = reading["tds"]
        old_turbidity = reading["turbidity"]

        # Guard check: if already swapped back (e.g. tds is low and turbidity is high, and this script is re-run)
        # However, for this one-time correction, we strictly swap them.
        new_tds = old_turbidity
        new_turbidity = old_tds

        # Update raw values in the database first so that subsequent history lookups fetch the corrected values!
        await (
            client.table("readings")
            .update({"tds": new_tds, "turbidity": new_turbidity})
            .eq("id", reading_id)
            .execute()
        )

        # Construct updated reading dict for ML pipeline
        updated_reading = {**reading, "tds": new_tds, "turbidity": new_turbidity}

        try:
            # Re-run ML pipeline manually to ensure we control history updates
            # 1. Validation & Imputation
            validated_inputs = validate_and_impute_reading(updated_reading)

            # 2. WQI
            wqi_score = calculate_wqi(
                validated_inputs["ph"],
                validated_inputs["tds"],
                validated_inputs["turbidity"],
            )

            # 3. Fetch corrected history (already written to DB for previous indices)
            history = await repo.get_recent_readings(user_id, limit=20)
            # Remove current reading from history
            history = [h for h in history if h.get("timestamp") != timestamp_str]

            # 4. EWMA features
            smoothed_features = compute_ewma_features(validated_inputs, history)

            # 5. XGBoost
            label, score, probs = run_xgb_inference(smoothed_features)

            # 6. Isolation Forest
            is_anomaly, anomaly_score = detect_anomaly(smoothed_features)

            # 7. SHAP
            shap_values = compute_exact_shap(smoothed_features, label)

            # 8. Recommendations
            recommendation, risk_level = generate_recommendation_and_risk(
                validated_inputs, label, is_anomaly
            )

            # 9. Update readings row in DB with WQI and label
            await repo.update_reading_ml(reading_id, wqi_score, label)

            # 10. Insert corrected ML results
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
                "recommendation": recommendation,
            }
            await repo.insert_ml_result(ml_res_payload)

            # 11. Process and generate alerts
            pipeline_result = {
                **updated_reading,
                "wqi_score": wqi_score,
                "label": label,
                "risk_level": risk_level,
                "recommendation": recommendation,
                "is_anomaly": is_anomaly,
                "anomaly_score": anomaly_score,
                "shap_values": shap_values,
                **probs,
            }

            # Generate and insert alerts (SSE publish is mocked to no-op)
            await alert_service.process_alerts(pipeline_result, client)

            corrected_count += 1
            if corrected_count % 50 == 0:
                print(f"Corrected {corrected_count}/{len(readings)} readings...")

        except Exception as e:
            print(f"Error correcting reading {reading_id}: {e}")

    print(f"Successfully corrected {corrected_count} readings for user {user_id}.")


async def main():
    print("Starting database readings correction script...")
    settings = get_settings()
    load_models()

    client = await create_async_client(
        settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY
    )

    # Fetch all active users to correct their readings
    users_res = await client.table("users").select("id").execute()
    users = users_res.data or []

    for user in users:
        await correct_readings_for_user(client, user["id"])

    print("Database correction complete!")


if __name__ == "__main__":
    asyncio.run(main())
