"""Model Loader and Self-Healing Trainer Service.

Loads, caches, and automatically trains XGBoost and Isolation Forest models.
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
import joblib
import structlog
from sklearn.ensemble import IsolationForest

logger = structlog.get_logger()

# Paths to saved models
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
XGB_PATH = os.path.join(MODEL_DIR, "xgboost_model.json")
IFOREST_PATH = os.path.join(MODEL_DIR, "isolation_forest.joblib")

# Singletons for loaded models
_xgb_model = None
_iforest_model = None


def generate_synthetic_data(num_samples: int = 1500) -> tuple[pd.DataFrame, pd.Series]:
    """Generates synthetic water quality dataset for training.
    
    Features: ph, tds, turbidity.
    Target: 0 (safe), 1 (borderline), 2 (unsafe).
    """
    np.random.seed(42)
    
    # 1. Generate safe/normal samples (Class 0)
    num_safe = num_samples // 3
    ph_safe = np.random.uniform(6.5, 8.5, num_safe)
    tds_safe = np.random.uniform(50.0, 300.0, num_safe)
    turb_safe = np.random.uniform(0.1, 5.0, num_safe)
    
    # 2. Generate borderline samples (Class 1)
    num_border = num_samples // 3
    # Mix of slightly elevated TDS or raised turbidity or slightly off pH
    ph_border = np.random.uniform(6.0, 9.0, num_border)
    tds_border = np.random.uniform(100.0, 600.0, num_border)
    turb_border = np.random.uniform(0.5, 15.0, num_border)
    
    # 3. Generate unsafe samples (Class 2)
    num_unsafe = num_samples - num_safe - num_border
    ph_unsafe = np.random.uniform(0.0, 14.0, num_unsafe)
    tds_unsafe = np.random.uniform(400.0, 2000.0, num_unsafe)
    turb_unsafe = np.random.uniform(10.0, 100.0, num_unsafe)
    
    # Combine
    ph = np.concatenate([ph_safe, ph_border, ph_unsafe])
    tds = np.concatenate([tds_safe, tds_border, tds_unsafe])
    turb = np.concatenate([turb_safe, turb_border, turb_unsafe])
    
    df = pd.DataFrame({"ph": ph, "tds": tds, "turbidity": turb})
    
    # Determine ground-truth labels based on criteria
    labels = []
    for _, row in df.iterrows():
        p, t, tu = row["ph"], row["tds"], row["turbidity"]
        # Unsafe rules
        if p < 6.0 or p > 9.0 or t > 600.0 or tu > 15.0:
            labels.append(2)  # Unsafe
        # Safe rules
        elif 6.5 <= p <= 8.5 and t <= 300.0 and tu <= 5.0:
            labels.append(0)  # Safe
        # Otherwise Borderline
        else:
            labels.append(1)  # Borderline
            
    return df, pd.Series(labels)


def train_and_save_models():
    """Trains the XGBoost and Isolation Forest models on synthetic data and saves them."""
    logger.info("ml_models_training_started", dest_dir=MODEL_DIR)
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Generate training data
    X, y = generate_synthetic_data()
    
    # Train XGBoost Classifier
    # nthread=1 for low latency single-row inference
    xgb_clf = xgb.XGBClassifier(
        n_estimators=50,
        max_depth=3,
        learning_rate=0.1,
        nthread=1,
        random_state=42,
        eval_metric="mlogloss"
    )
    xgb_clf.fit(X, y)
    xgb_clf.save_model(XGB_PATH)
    logger.info("ml_xgb_model_saved", path=XGB_PATH)
    
    # Train Isolation Forest on nominal (safe) data only
    X_safe = X[y == 0]
    iforest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
        n_jobs=1
    )
    iforest.fit(X_safe)
    joblib.dump(iforest, IFOREST_PATH)
    logger.info("ml_iforest_model_saved", path=IFOREST_PATH)


def load_models(force_retrain: bool = False):
    """Loads XGBoost and Isolation Forest models into memory."""
    global _xgb_model, _iforest_model
    
    if force_retrain or not os.path.exists(XGB_PATH) or not os.path.exists(IFOREST_PATH):
        logger.info("ml_models_not_found_or_retrain_requested", force_retrain=force_retrain)
        train_and_save_models()
        
    try:
        # Load XGBoost model
        # Use Booster for high performance or XGBClassifier wrapper
        # Using XGBClassifier allows keeping the Scikit-learn API wrapper if needed, 
        # but loading as raw Booster is also very clean. Let's load as XGBClassifier.
        clf = xgb.XGBClassifier()
        clf.load_model(XGB_PATH)
        _xgb_model = clf
        logger.info("ml_xgb_model_loaded", path=XGB_PATH)
        
        # Load Isolation Forest
        _iforest_model = joblib.load(IFOREST_PATH)
        logger.info("ml_iforest_model_loaded", path=IFOREST_PATH)
    except Exception as e:
        logger.error("ml_model_loading_failed", error=str(e))
        # Self-healing fallback: force retraining if load failed (e.g. corruption)
        if not force_retrain:
            logger.warning("ml_attempting_self_healing_retrain")
            load_models(force_retrain=True)
        else:
            raise e


def get_xgb_model():
    """Gets the cached XGBoost model instance, loading it if necessary."""
    global _xgb_model
    if _xgb_model is None:
        load_models()
    return _xgb_model


def get_iforest_model():
    """Gets the cached Isolation Forest model instance, loading it if necessary."""
    global _iforest_model
    if _iforest_model is None:
        load_models()
    return _iforest_model
