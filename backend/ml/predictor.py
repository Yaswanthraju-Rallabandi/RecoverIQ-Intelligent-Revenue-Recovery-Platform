import os
import joblib
import pandas as pd
from typing import Dict, Any, Tuple

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved_models", "recovery_model_v1.joblib")

_model = None

def get_model():
    global _model
    if _model is None:
        if os.path.exists(MODEL_PATH):
            _model = joblib.load(MODEL_PATH)
        else:
            print("[WARN] Model file not found, triggering auto-training...")
            from .train import train_recovery_model
            train_recovery_model()
            _model = joblib.load(MODEL_PATH)
    return _model

def predict_single_probability(
    amount: float,
    method: str,
    failure_code: str,
    attempt_number: int,
    hour_of_day: int,
    past_successful_payments: int,
    action_type: str
) -> Tuple[float, str]:
    """
    Returns calibrated probability (0.0 to 100.0) and confidence level.
    """
    model = get_model()
    
    row = pd.DataFrame([{
        "amount": float(amount),
        "method": str(method),
        "failure_code": str(failure_code),
        "attempt_number": int(attempt_number),
        "hour_of_day": int(hour_of_day),
        "past_successful_payments": int(past_successful_payments),
        "action_type": str(action_type)
    }])
    
    try:
        prob = float(model.predict_proba(row)[0][1]) * 100.0
        prob = max(3.0, min(95.0, round(prob, 1)))
    except Exception as e:
        print(f"Inference error: {e}, falling back to empirical prior")
        prob = 50.0
        
    conf = "HIGH" if (prob >= 70.0 or prob <= 20.0) else ("MEDIUM" if prob >= 45.0 else "LOW")
    return prob, conf