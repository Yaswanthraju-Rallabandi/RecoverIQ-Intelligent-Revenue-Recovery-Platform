# REVORA | AI Revenue Recovery and Optimization Engine
### Razorpay AI Hackathon | Track 3: AI Revenue Recovery

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Razorpay SDK](https://img.shields.io/badge/Razorpay-API%20Integration-0c8cee.svg)](https://razorpay.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Calibrated%20Ensemble-f89939.svg)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

REVORA is an autonomous financial intelligence platform that discovers, prioritizes, and recovers delinquent revenue across failed checkout payments, abandoned partial balances, overdue B2B invoices, and gateway authorization mismatches.

Rather than relying on naive chronological retries or greedy expected-value sorting, REVORA formulates recovery as an exact resource-constrained 0/1 Knapsack Dynamic Program, selecting the optimal combination of recovery actions that maximizes expected yield within merchant operational budgets.

---

## Key Technical Innovations

### 1. Resource-Constrained 0/1 Knapsack Optimization
Most recovery tools execute retries greedily or by arrival time. In production, merchants have finite daily action quotas and notification fatigue budgets (W).
- Greedy sorting by raw expected value frequently selects heavy, resource-intensive opportunities that crowd out bundles of higher-efficiency recoveries.
- REVORA implements an exact 0/1 Knapsack Dynamic Programming Optimizer alongside a Counterfactual Backtest Simulator, mathematically proving lift over greedy and first-in-first-out (FIFO) heuristics.

$$\max \sum_{i=1}^{M} x_i \cdot \text{EV}_i \quad \text{subject to} \quad \sum_{i=1}^{M} x_i \cdot w_i \le W, \quad x_i \in \{0, 1\}$$

### 2. AI Explains, Code Decides (Deterministic Guardrails)
Probabilistic machine learning models should never hold autonomous authority to execute financial debits.
- **Deterministic Code**: Enforces strict spending ceilings (INR 25,000 threshold), issuer switch health checks, customer cooldown windows (15 minutes), pre-auth capture safety windows (24-110h), and Razorpay API execution.
- **Explainable AI Layer**: Produces plain-text economic rationales, trade-off explanations, and root-cause diagnoses after mathematical boundaries are validated.
- **Confidence-Gated Quarantining**: High-value transactions with low confidence are automatically quarantined for merchant sign-off.

### 3. Six Statistical Judgment Layers
1. **Expected Value Confidence Intervals**: Binomial variance propagation computes a 90% confidence interval alongside point predictions (e.g., INR 20,028 - INR 59,572 [90% CI]).
2. **Knapsack Rejected Candidate Explanations**: Dedicated audit drawer displaying passed-over opportunities with explicit economic trade-off rationales.
3. **Model Calibration and Brier Score Verification**: Evaluates model reliability with a Brier Score of 0.1142, Brier Skill Score of +54.3%, and decile calibration tables.
4. **Pre-Authorization Auto-Capture Guardrail**: Enforces an INR 7,500 safety ceiling and 24-110h validity horizon to prevent unauthorized captures.
5. **Continuous Learning Feedback Loop**: Captures real-world settlement outcomes (`POST /feedback/record-outcome`) to update empirical weights and eliminate drift.
6. **7-Day Compounding Recovery Analytics**: Tracks rolling recovery rates and cumulative recovered liquidity over time.

---

## System Architecture Pipeline

$$\Large \text{Detect} \longrightarrow \text{Predict} \longrightarrow \text{Calculate} \longrightarrow \text{Optimize} \longrightarrow \text{Guard} \longrightarrow \text{Recover} \longrightarrow \text{Verify} \longrightarrow \text{Measure}$$

```
Multi-Source Transaction Ingestion
  |-- 1. Failed Payments (Switch timeouts, 3DS drop-offs)
  |-- 2. Partial Payments (Tokenized milestone balances)
  |-- 3. Overdue Invoices (B2B aging receivables)
  \-- 4. Refund Mismatches (Uncaptured pre-authorization charges)
         |
         v
Unified Normalization and Telemetry Ingestion
         |
         v
Calibrated Machine Learning Probability Predictor
  * 5-Fold Platt Scaled Random Forest Ensemble (ROC-AUC 0.7206)
  * Feature normalization via ColumnTransformer and OneHotEncoder
         |
         v
Expected Value (EV) Formulation with Binomial CI
  EV = (P_recovery * Recoverable Amount) - Action Cost
         |
         v
Constrained 0/1 Knapsack Dynamic Program
  * Computes global optimal subset under merchant effort budget
  * Logs excluded candidates with explicit economic trade-offs
         |
         v
Deterministic Safety Guardrails and Governance
  * Spend limits, retry quotas, cooldowns, pre-auth safety windows
         |
         v
Live Razorpay Gateway Execution and Cloud Reconciliation
  * Dynamic payment links (plink_...) via Razorpay REST API
  * Real-time payment state polling and HMAC-SHA256 verification
         |
         v
Financial Dashboard and Continuous Learning Feedback
```

---

## Opportunity Detectors

| Detector | Category | Trigger Condition | Automated Action |
| :--- | :--- | :--- | :--- |
| **failed_payment** | Checkout Drop-Offs | Gateway switch timeouts and authentication failures | Smart delayed retry with 15m cooldown backoff |
| **partial_payment** | Tokenized Advances | Order balance remaining (`paid_amount < total_amount`) | Dynamic Razorpay payment link with custom balance |
| **overdue_payment** | B2B Receivables | Invoices past net terms with low dispute risk | 1-Click UPI deep-link and automated payment plan |
| **refund_mismatch** | Gateway Glitches | Authorized charges uncaptured within 5-day window | Automated pre-auth capture before authorization TTL |

---

## Machine Learning Specification

- **Primary Classifier**: `RandomForestClassifier(n_estimators=100, max_depth=7, min_samples_split=8)`
- **Calibration Method**: `CalibratedClassifierCV(method="sigmoid", cv=5)` (5-fold Platt Scaling)
- **Baseline Benchmark**: `LogisticRegression(max_iter=500)` for feature coefficient verification
- **Evaluation Metrics (Held-Out 20% Stratified Test Set)**:
  - **Recall**: 89.23% (minimizes false negatives in recoverable cash flow)
  - **Precision**: 69.64%
  - **F1-Score**: 0.7823
  - **ROC-AUC**: 0.7206
  - **Brier Score**: 0.1142 (well below 0.25 random threshold)
  - **Brier Skill Score**: +54.3% lift over uninformative baseline
  - **Mean Calibration Error**: 2.6% to 3.1% across decile probability bins

---

## Project Structure

```
.
|-- backend/
|   |-- detectors/               # 4 Modular Opportunity Detectors
|   |   |-- base.py
|   |   |-- failed_payment_detector.py
|   |   |-- overdue_invoice_detector.py
|   |   |-- partial_payment_detector.py
|   |   \-- refund_mismatch_detector.py
|   |-- engine/                  # Core Algorithmic Optimization & Policy Engines
|   |   |-- actions.py           # Action definitions and cost matrix
|   |   |-- ai_explainer.py      # Plain-language explanation generator
|   |   |-- backtest.py          # Counterfactual simulation engine
|   |   |-- decision_engine.py   # Decision orchestrator
|   |   |-- guardrails.py        # Deterministic financial safety checks
|   |   |-- opportunity_engine.py# Normalization pipeline
|   |   |-- optimizer.py         # 0/1 Knapsack DP & candidate trade-offs
|   |   \-- trends.py            # 7-day compounding performance metrics
|   |-- ml/                      # Machine Learning Subsystem
|   |   |-- calibration.py       # Brier score and reliability curves
|   |   |-- dataset_generator.py # Domain-informed empirical simulation
|   |   |-- feedback.py          # Closed-loop outcome tracking
|   |   |-- predictor.py         # Real-time inference engine
|   |   |-- saved_models/        # Serialized joblib artifacts and metadata
|   |   \-- train.py            # Stratified training pipeline
|   |-- payments/                # Payment Gateway Integration
|   |   |-- razorpay_client.py   # Official Razorpay SDK wrapper
|   |   \-- webhook_handler.py   # Webhook ingestion and HMAC verification
|   |-- database.py              # SQLite / PostgreSQL engine setup
|   |-- main.py                  # FastAPI application and route controllers
|   |-- models.py                # SQLAlchemy 13-table schema
|   \-- seed.py                 # Multi-scenario database seeder
|-- data/                        # Schema definitions and sample datasets
|-- static/                      # Modern Fintech Dashboard UI
|   \-- index.html              # Responsive dark-mode single-page application
|-- .env.example                 # Sanitized environment template
|-- ARCHITECTURE.md              # Technical design whitepaper
|-- PITCH_DEMO_SCRIPT.md         # Video demonstration pitch script
\-- requirements.txt            # Python dependency requirements
```

---

## Quick Start and Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Yaswanthraju-Rallabandi/ReviveX-Intelligent-Revenue-Recovery-Platform.git
cd ReviveX-Intelligent-Revenue-Recovery-Platform
```

### 2. Environment Configuration
Copy `.env.example` to `.env` and add your Razorpay test credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
RAZORPAY_KEY_ID=rzp_test_your_key_here
RAZORPAY_KEY_SECRET=your_key_secret_here
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret_here
PORT=8000
```

### 3. Install Dependencies
```bash
py -m pip install fastapi uvicorn sqlalchemy pydantic scikit-learn joblib python-dotenv razorpay
```

### 4. Initialize Database and Train Model
```bash
# Generate training dataset and train calibrated ensemble
py backend/ml/train.py

# Seed database with sample multi-channel opportunities
py backend/seed.py
```

### 5. Run Verification Suite
```bash
py backend/audit_full_app.py
```

### 6. Start Server
```bash
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 7. Access Live Dashboard
Open your browser to:
- **Dashboard UI**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Swagger API Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Core API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/stats` | Executive financial summary, recovery rates, and segmented breakdowns |
| `GET` | `/opportunities` | Prioritized queue sorted by 0/1 Knapsack optimization |
| `GET` | `/optimize` | Solves 0/1 knapsack dynamic program given capacity budget |
| `GET` | `/backtest-simulation` | Counterfactual backtest comparing Knapsack DP vs Greedy vs FIFO |
| `GET` | `/model-calibration` | Brier score, Brier skill score, and decile reliability bins |
| `GET` | `/analytics/trends` | 7-day compounding recovery performance metrics |
| `GET` | `/feedback/metrics` | Continuous learning tracking, resolution times, and model accuracy |
| `POST` | `/opportunities/{id}/recover` | Executes 1-click Razorpay payment link or smart recovery action |
| `POST` | `/feedback/record-outcome` | Ingests real payment outcome to close the feedback loop |
| `POST` | `/reset-demo` | Resets all opportunities back to unrecovered state for clean demos |
| `POST` | `/webhooks/razorpay` | Receives live Razorpay webhooks with HMAC-SHA256 verification |

---

## License & Attribution
Developed for the **Razorpay AI Hackathon | Track 3: AI Revenue Recovery**. Released under the [MIT License](LICENSE).
