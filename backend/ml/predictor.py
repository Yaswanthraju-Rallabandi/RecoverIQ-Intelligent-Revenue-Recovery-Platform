import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import joblib
import pandas as pd
from typing import Tuple, Dict, Any

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models", "recoveriq_recovery_model_v1.joblib")
_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            print("[WARN] ML Model artifact not found. Training model...")
            try:
                from train import train_recoveriq_model
            except ImportError:
                from .train import train_recoveriq_model
            train_recoveriq_model()
            _model = joblib.load(MODEL_PATH)
    return _model

def predict_single_probability(
    amount: float,
    method: str = "upi",
    opportunity_type: str = "failed_payment",
    age_days: int = 1,
    customer_risk: str = "LOW",
    past_successful_payments: int = 4,
    past_late_payments: int = 0,
    retry_count: int = 0
) -> Tuple[float, str]:
    """
    Scores any opportunity regardless of type. Returns calibrated recovery probability (0.0 to 100.0%) and confidence level.
    """
    model = get_model()
    row = pd.DataFrame([{
        "opportunity_type": str(opportunity_type),
        "amount": float(amount),
        "payment_method": str(method),
        "age_days": int(age_days),
        "customer_risk": str(customer_risk),
        "past_successful_payments": int(past_successful_payments),
        "past_late_payments": int(past_late_payments),
        "retry_count": int(retry_count)
    }])

    try:
        prob = float(model.predict_proba(row)[0][1]) * 100.0
        prob = max(4.0, min(95.0, round(prob, 1)))
    except Exception as e:
        print(f"Inference fallback: {e}")
        prob = 55.0

    conf = "HIGH" if (prob >= 70.0 or prob <= 25.0) else ("MEDIUM" if prob >= 45.0 else "LOW")
    return prob, conf