#  REVORA — AI Revenue Recovery & Optimization Engine
### *Razorpay AI Hackathon — Track 3: AI Revenue Recovery*

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Razorpay Test Mode](https://img.shields.io/badge/Razorpay-Test%20Mode-0c8cee.svg)](https://razorpay.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **REVORA** is an autonomous financial intelligence platform that discovers hidden revenue-recovery opportunities across **failed payments, partial payments, overdue invoices, and gateway reconciliation mismatches**. It formulates recovery as an exact **resource-constrained 0/1 Knapsack Dynamic Program** that chooses the mathematical combination of actions that maximizes recovered revenue within a merchant's operational budget.

---

##  The Two Core Differentiators

### 1. Resource-Constrained Knapsack Optimization (Not Just Sorting)
Most revenue recovery tools either retry checkout failures chronologically or greedily sort by expected value. But merchants have **finite daily action capacity / operational budgets** ($N$).
- Sorting greedily by Expected Value often picks bulky, low-efficiency opportunities that block multiple high-efficiency recoveries.
- REVORA implements an exact **0/1 Knapsack Dynamic Programming Optimizer** alongside a **Counterfactual Backtest Simulator**, delivering proven mathematical lift over naive FIFO and greedy heuristics.

$$\max \sum_{i=1}^{M} x_i \cdot \text{EV}_i \quad \text{subject to} \quad \sum_{i=1}^{M} x_i \cdot w_i \le N, \quad x_i \in \{0, 1\}$$

### 2. AI Explains, But Code Decides (Deterministic Guardrails)
Probabilistic AI models and LLMs should never have direct control over moving money or executing financial transactions.
- **Deterministic Code**: Enforces calculations, optimization, state transitions, spending caps (Rs 25,000 limit), fraud deny-lists, cooldowns, and Razorpay API execution.
- **AI Explanation Layer**: Generates plain-language root-cause diagnoses and action rationales **after** the deterministic decision is made.
- **Confidence-Gated Review**: High-value transactions (>Rs 10,000) with low AI confidence (<60%) are quarantined for merchant manual sign-off.

---

##  The 8-Stage Architecture Pipeline

$$\Large \text{Detect} \longrightarrow \text{Predict} \longrightarrow \text{Calculate} \longrightarrow \text{Optimize} \longrightarrow \text{Guard} \longrightarrow \text{Recover} \longrightarrow \text{Verify} \longrightarrow \text{Measure}$$

```
Merchant / Razorpay Business Data
        ↓
1. Multi-Source Ingestion & 4 Modular Detectors
   (failed_payment, partial_payment, overdue_payment, refund_mismatch)
        ↓
2. Unified Opportunity Normalization (ID, type, amount, customer, telemetry)
        ↓
3. ML Recovery Probability Predictor (Calibrated Random Forest Pipeline)
        ↓
4. Expected Value (EV) Formulation:
   EV = (P_recovery × Recoverable Amount) − Action Cost
        ↓
5. Constrained 0/1 Knapsack Optimization Engine:
   [ 0/1 Dynamic Programming Knapsack vs Greedy Ratio vs Naive FIFO ]
        ↓
6. Deterministic Safety Guardrails & Confidence Gating
        ↓
7. Razorpay Test-Mode Execution & Webhook Idempotency
   (Smart Retries, Dynamic Payment Links, Pre-Auth Capture)
        ↓
8. Executive Financial Dashboard & Counterfactual Analytics
```

---

##  The 4 Revenue Opportunity Detectors

| Detector | Category | Trigger Logic | Operational Action |
| :--- | :--- | :--- | :--- |
| **1. `failed_payment`** | Checkout Drop-Offs | Scans gateway authorization switch timeouts & 3DS OTP drop-offs. | Smart delayed switch retry with 15m cooldown backoff. |
| **2. `partial_payment`** | Tokenized Advances | Scans orders where `paid_amount < total_amount` (balance abandoned). | Dispatches dynamic Razorpay balance payment link via WhatsApp. |
| **3. `overdue_payment`** | B2B & Mandates | Scans corporate SaaS invoices & recurring mandates past due terms. | 1-Click UPI Deep-link with dynamic payment schedule. |
| **4. `refund_mismatch`** | Gateway Glitches | Scans uncaptured pre-authorized charges nearing 5-day TTL window. | Auto-captures authorized charge and reconciles rail. |

---

##  Database Schema (13 Relational Tables)

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

##  Quick Start & Installation

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
py backend/audit_full_app.py
```

### 4. Run the REVORA Server
```bash
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 5. Open the Dashboard
Open **http://127.0.0.1:8000/** in your browser to view the live dashboard!

---

##  Live API Endpoints

- **`GET /stats`**: Executive financial recovery ribbon segmented by opportunity type.
- **`GET /opportunities`**: Prioritized opportunity queue ordered by Day 5 Knapsack optimization.
- **`GET /optimize`**: Solves resource-constrained knapsack under budget $N$.
- **`GET /backtest-simulation`**: Counterfactual simulation comparing DP vs Naive EV sorting vs FIFO.
- **`POST /predict-recovery`**: Real-time ML inference returning calibrated probability and EV.
- **`POST /opportunities/{id}/recover`**: Executes 1-click Razorpay Test Mode action.
- **`POST /webhooks/razorpay`**: Webhook callback listener with strict idempotency verification.
- **`POST /simulate-webhook`**: Live webhook trigger tool for hackathon judging & demos.
- **`GET /docs`**: Interactive Swagger API documentation.

---

##  Key Documentation Files
- **[`ARCHITECTURE.md`](./ARCHITECTURE.md)**: Master technical whitepaper covering mathematics, database schema, and safety boundaries.
- **[`PITCH_DEMO_SCRIPT.md`](./PITCH_DEMO_SCRIPT.md)**: 5-Minute video pitch script with timestamped narration and demo flow.

---

##  Authors
Built for the **Razorpay AI Hackathon — Track 3: AI Revenue Recovery**.