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
    from dataset_generator import generate_revora_ml_dataset
except ImportError:
    from .dataset_generator import generate_revora_ml_dataset

def train_revora_model():
    data_path = "data/revora_ml_training_data.csv"
    if not os.path.exists(data_path):
        generate_revora_ml_dataset(3500, data_path)

    df = pd.read_csv(data_path)
    print(f"[1] Loaded training dataset: {len(df)} samples. Distribution: {df['recovered'].value_counts().to_dict()}")

    categorical_features = ["opportunity_type", "payment_method", "customer_risk"]
    numeric_features = ["amount", "age_days", "past_successful_payments", "past_late_payments", "retry_count"]

    X = df[categorical_features + numeric_features]
    y = df["recovered"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_features),
            ("num", StandardScaler(), numeric_features)
        ]
    )

    # 1. Baseline Model: Logistic Regression
    lr_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("classifier", LogisticRegression(max_iter=500, random_state=42))
    ])
    lr_pipeline.fit(X_train, y_train)
    lr_auc = float(roc_auc_score(y_test, lr_pipeline.predict_proba(X_test)[:, 1]))
    print(f"[2] Baseline Logistic Regression ROC-AUC: {lr_auc:.4f}")

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

    print("\n" + "=" * 65)
    print(">>> DAY 4: REVORA ML MODEL EVALUATION (HELD-OUT 20% TEST SET)")
    print("=" * 65)
    print(f"   Accuracy:  {acc * 100:.2f}%")
    print(f"   Precision: {prec * 100:.2f}%")
    print(f"   Recall:    {rec * 100:.2f}%")
    print(f"   F1-Score:  {f1 * 100:.2f}%")
    print(f"   ROC-AUC:   {auc:.4f} (Calibrated Ensemble vs {lr_auc:.4f} Baseline)")
    print(f"   Confusion Matrix: TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}, TP={cm[1][1]}")
    print("=" * 65 + "\n")

    # Feature Importance Inspection
    cat_names = rf_pipeline.named_steps["preprocessor"].named_transformers_["cat"].get_feature_names_out(categorical_features).tolist()
    all_feature_names = cat_names + numeric_features
    importances = rf_base.feature_importances_

    ranking = sorted(zip(all_feature_names, importances), key=lambda x: x[1], reverse=True)
    print(">>> TOP 6 PREDICTIVE RECOVERY FEATURES:")
    for feat, imp in ranking[:6]:
        print(f"   - {feat:35s}: {imp * 100:.2f}%")
    print()

    # Persist Artifact
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_models")
    os.makedirs(save_dir, exist_ok=True)
    model_file = os.path.join(save_dir, "revora_recovery_model_v1.joblib")
    meta_file = os.path.join(save_dir, "model_metadata.json")

    joblib.dump(calibrated_rf, model_file)

    meta = {
        "model_version": "revora-rf-calibrated-v1",
        "algorithm": "RandomForestClassifier(n_estimators=100, max_depth=7) + Platt Scaling",
        "baseline_logistic_auc": round(lr_auc, 4),
        "roc_auc": round(auc, 4),
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "features": categorical_features + numeric_features,
        "trained_at": datetime.now(timezone.utc).isoformat()
    }
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2)

    print(f"[SUCCESS] Model artifact saved to: {model_file}")
    return meta

if __name__ == "__main__":
    train_revora_model()