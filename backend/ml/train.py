import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timezone

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix
)

try:
    from dataset_generator import generate_recoveriq_ml_dataset
except ImportError:
    from .dataset_generator import generate_recoveriq_ml_dataset

def train_recoveriq_model():
    data_path = "data/recoveriq_ml_training_data.csv"
    if not os.path.exists(data_path):
        generate_recoveriq_ml_dataset(4000, data_path)

    df = pd.read_csv(data_path)
    print(f"[1] Loaded dataset: {len(df)} samples across 4 opportunity types.")
    print(f"    Class Balance: Recovered(1)={sum(df['recovered']==1)}, Failed(0)={sum(df['recovered']==0)}")

    categorical_features = ["opportunity_type", "payment_method", "customer_risk"]
    numeric_features = ["amount", "age_days", "past_successful_payments", "past_late_payments", "retry_count"]

    X = df[categorical_features + numeric_features]
    y = df["recovered"]

    # 80/20 Stratified Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )
    print(f"[2] Split: {len(X_train)} Train Samples | {len(X_test)} Held-Out Test Samples")

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", StandardScaler(), numeric_features)
        ]
    )

    # 1. Train Interpretable Logistic Regression (To inspect feature coefficients)
    lr_model = LogisticRegression(max_iter=500, random_state=42)
    lr_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", lr_model)
    ])
    lr_pipeline.fit(X_train, y_train)
    
    lr_y_prob = lr_pipeline.predict_proba(X_test)[:, 1]
    lr_auc = float(roc_auc_score(y_test, lr_y_prob))

    # Extract all feature names from OneHotEncoder + Numeric
    cat_names = lr_pipeline.named_steps["preprocessor"].named_transformers_["cat"].get_feature_names_out(categorical_features).tolist()
    all_feature_names = cat_names + numeric_features
    lr_coefficients = lr_model.coef_[0]

    print("\n" + "=" * 70)
    print(">>> SANITY CHECK: LOGISTIC REGRESSION FEATURE COEFFICIENTS")
    print("=" * 70)
    coef_ranking = sorted(zip(all_feature_names, lr_coefficients), key=lambda x: x[1], reverse=True)
    for feat, coef in coef_ranking:
        direction = "(+ Boosts Recovery)" if coef > 0 else "(- Reduces Recovery)"
        print(f"   {feat:40s}: {coef:+6.3f}  {direction}")
    print("=" * 70)

    # 2. Main Model: Calibrated Random Forest Ensemble
    rf_base = RandomForestClassifier(
        n_estimators=100,
        max_depth=7,
        min_samples_split=8,
        random_state=42
    )

    rf_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", rf_base)
    ])

    calibrated_rf = CalibratedClassifierCV(
        estimator=rf_pipeline,
        method="sigmoid",
        cv=5
    )
    calibrated_rf.fit(X_train, y_train)
    rf_pipeline.fit(X_train, y_train)

    y_pred = calibrated_rf.predict(X_test)
    y_prob = calibrated_rf.predict_proba(X_test)[:, 1]

    acc = float(accuracy_score(y_test, y_pred))
    prec = float(precision_score(y_test, y_pred))
    rec = float(recall_score(y_test, y_pred))
    f1 = float(f1_score(y_test, y_pred))
    auc = float(roc_auc_score(y_test, y_prob))
    cm = confusion_matrix(y_test, y_pred).tolist()

    print("\n" + "=" * 70)
    print(">>> DAY 4: RecoverIQ ML MODEL EVALUATION (HELD-OUT 20% TEST SET)")
    print("=" * 70)
    print(f"   Accuracy:  {acc * 100:.2f}%")
    print(f"   Precision: {prec * 100:.2f}% (High quality positive recovery predictions)")
    print(f"   Recall:    {rec * 100:.2f}%")
    print(f"   F1-Score:  {f1 * 100:.2f}%")
    print(f"   ROC-AUC:   {auc:.4f} (Calibrated Ensemble vs {lr_auc:.4f} Logistic Baseline)")
    print(f"   Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
    print("=" * 70 + "\n")

    # Persist Artifact
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
    os.makedirs(save_dir, exist_ok=True)
    model_file = os.path.join(save_dir, "recoveriq_recovery_model_v1.joblib")
    meta_file = os.path.join(save_dir, "model_metadata.json")

    joblib.dump(calibrated_rf, model_file)

    meta = {
        "model_version": "recoveriq-rf-calibrated-v1",
        "algorithm": "RandomForestClassifier(n_estimators=100, max_depth=7) + 5-Fold Platt Scaling",
        "baseline_logistic_auc": round(lr_auc, 4),
        "roc_auc": round(auc, 4),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm,
        "features": categorical_features + numeric_features,
        "trained_at": datetime.now(timezone.utc).isoformat()
    }
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[SUCCESS] Model artifact persisted to: {model_file}")
    return meta

if __name__ == "__main__":
    train_recoveriq_model()