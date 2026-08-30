# 🚀 REVORA — AI Revenue Recovery & Optimization Engine
### *Razorpay AI Hackathon — Track 3: AI Revenue Recovery*

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Razorpay Test Mode](https://img.shields.io/badge/Razorpay-Test%20Mode-0c8cee.svg)](https://razorpay.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **REVORA** is an autonomous financial intelligence and constrained optimization engine designed to discover hidden revenue-recovery opportunities across **failed payments, partial payments, overdue invoices, and reconciliation mismatches**. It uses calibrated machine learning to estimate recovery probabilities, computes Expected Financial Value, and formulates recovery as a **resource-constrained 0/1 knapsack optimization problem** to determine the exact combination of actions that maximizes merchant cash flow.

---

## 📌 The Central Innovation: Resource-Constrained Optimization

### The Problem:
Most revenue recovery systems simply retry checkout failures or sort opportunities chronologically. In reality:
- Merchants have a **limited daily action capacity / operational budget** ($N$ opportunities or $W$ action effort).
- Opportunities have different recoverable amounts, recovery probabilities, and operational action costs.

### The Question Answered by REVORA:
> **"If a merchant can act on only $N$ opportunities today, which combination will maximize total expected recovered revenue?"**

$$\max \sum_{i=1}^{M} x_i \cdot \text{EV}_i \quad \text{subject to} \quad \sum_{i=1}^{M} x_i \cdot w_i \le N, \quad x_i \in \{0, 1\}$$

---

## 🔄 The 8-Stage Architecture Pipeline

$$\Large \text{Detect} \longrightarrow \text{Predict} \longrightarrow \text{Calculate} \longrightarrow \text{Optimize} \longrightarrow \text{Guard} \longrightarrow \text{Recover} \longrightarrow \text{Verify} \longrightarrow \text{Measure}$$

```
Merchant / Razorpay Business Data
        ↓
1. Multi-Source Ingestion & 4 Opportunity Detectors
   (failed_payment, partial_payment, overdue_payment, refund_mismatch)
        ↓
2. Unified Opportunity Normalization (ID, type, amount, customer, telemetry)
        ↓
3. ML Recovery Probability Predictor (Calibrated Random Forest Pipeline)
        ↓
4. Expected Value (EV) Formulation:
   EV = (P_recovery × Recoverable Amount) − Action Cost
        ↓
5. Constrained Optimization Engine:
   [ 0/1 Dynamic Programming Knapsack vs Greedy Ratio vs Naive FIFO ]
        ↓
6. Deterministic Safety Guardrails (Spend Cap, Cooldown, Fraud Quarantine)
        ↓
7. 1-Click Recovery Action (Razorpay Test Mode Dynamic Payment Links)
        ↓
8. Real-Time Merchant Dashboard (Revenue at Risk, Predicted EV, Settled ₹)
```

---

## 🎯 The 4 Revenue Opportunity Detectors

| Detector | Category | Trigger Logic | Operational Action |
| :--- | :--- | :--- | :--- |
| **① `failed_payment`** | Checkout Drop-Offs | Scans gateway authorization switch timeouts & 3DS OTP drop-offs. | Smart delayed switch retry with 15m cooldown backoff. |
| **② `partial_payment`** | Tokenized Advances | Scans orders where `paid_amount < total_amount` (balance abandoned). | Dispatches dynamic Razorpay balance payment link via WhatsApp. |
| **③ `overdue_payment`** | B2B & Mandates | Scans corporate SaaS invoices & recurring mandates past due terms. | 1-Click UPI Deep-link with dynamic payment schedule. |
| **④ `refund_mismatch`** | Gateway Glitches | Scans uncaptured pre-authorized charges nearing 5-day TTL window. | Auto-captures authorized charge and reconciles rail. |

---

## 📊 Database Schema (13 Relational Tables)

REVORA is architected with 13 relational tables in SQLite / PostgreSQL:

1. **`users`**: Merchant user accounts and role-based permissions.
2. **`merchants`**: Merchant profiles, daily action capacity budget $N$, and spend cap policies.
3. **`customers`**: Customer profiles, risk scores (`LOW`, `MEDIUM`, `HIGH`), and payment history.
4. **`payments`**: Raw checkout transactions and failure codes.
5. **`invoices`**: B2B invoices, amounts, due dates, and partial payment records.
6. **`refunds`**: Gateway reconciliation records and pre-authorization mismatch states.
7. **`revenue_opportunities`**: The unified opportunity entity storing type, recoverable amount, EV, and status.
8. **`recovery_predictions`**: ML probability outputs, confidence levels, and feature snapshots.
9. **`recovery_actions`**: Candidate operational actions, costs, and knapsack effort weights.
10. **`guardrail_events`**: Detailed pass/fail logs for safety policies.
11. **`webhook_events`**: Idempotency ledger preventing duplicate event execution.
12. **`audit_logs`**: Immutable, append-only audit trail recording every recovery event.
13. **`model_versions`**: ML model registry storing ROC-AUC, Precision, Recall, and version tags.

---

## 🧠 ML Model Pipeline & Evaluation (Day 4)

- **Dataset**: 3,500 realistic ground-truth training records (`data/revora_ml_training_data.csv`).
- **Algorithm**: Ensemble `RandomForestClassifier` with 5-Fold Platt Scaling (`CalibratedClassifierCV`).
- **Features**: `opportunity_type`, `payment_method`, `customer_risk`, `amount`, `age_days`, `past_successful_payments`, `past_late_payments`, `retry_count`.
- **Evaluation on Held-Out 20% Test Split (700 samples)**:
  - **ROC-AUC**: **0.7206** (vs 0.7224 Baseline Logistic Regression)
  - **Accuracy**: **67.71%**
  - **Precision**: **69.64%**
  - **Recall**: **89.23%**
  - **F1-Score**: **78.23%**
- **Persistence**: Saved to `backend/ml/saved_models/revora_recovery_model_v1.joblib`.

---

## 🛡️ Deterministic Safety Guardrails

- **Spend Cap Policy**: Caps autonomous actions at **₹25,000**. High-value opportunities require merchant sign-off.
- **Fraud Deny-List**: Accounts flagged as `HIGH` risk are quarantined immediately.
- **Attempt Caps**: Strict 3-retry maximum to prevent gateway velocity limits.
- **Mandatory Cooldowns**: Enforces 15-minute backoff intervals.

---

## ⚡ Quick Start & Installation

### 1. Install Dependencies
```bash
py -m pip install fastapi uvicorn sqlalchemy pydantic scikit-learn joblib
```

### 2. Seed Database & Train ML Model
```bash
py backend/ml/train.py
py backend/seed.py
```

### 3. Run Test Suite
```bash
py backend/test_day1_to_day4.py
```

### 4. Run the REVORA Server
```bash
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Open the Dashboard
Open **http://127.0.0.1:8000/** in your browser to view the live dashboard and execute 1-click recoveries!

---

## 📡 Live API Endpoints

- **`GET /stats`**: Executive financial recovery ribbon (Revenue at Risk, Predicted EV, Settled ₹, Recovery Rate %).
- **`GET /opportunities`**: Prioritized list of unified revenue opportunities with filter support.
- **`POST /detect-opportunities`**: Triggers all 4 detectors live across raw merchant records.
- **`POST /predict-recovery`**: Real-time ML inference returning calibrated probability and EV.
- **`POST /opportunities/{id}/recover`**: Executes 1-click Razorpay Test Mode dynamic payment link.
- **`GET /docs`**: Interactive Swagger API documentation.

---

## 👥 Authors
Built for the **Razorpay AI Hackathon — Track 3: AI Revenue Recovery**.