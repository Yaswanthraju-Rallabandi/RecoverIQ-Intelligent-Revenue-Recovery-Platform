# 🚀 RevoFlow — AI Revenue Optimization & Recovery
### *Razorpay AI Hackathon (Track 3: AI Revenue Recovery)*

[![Python 3.13](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Razorpay Test Mode](https://img.shields.io/badge/Razorpay-Test%20Mode-0c8cee.svg)](https://razorpay.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **RevoFlow** is an autonomous financial intelligence engine that discovers hidden revenue-recovery opportunities across **failed payments, partial payments, and overdue receivables**. It uses machine learning to estimate recovery probability, calculates the expected financial value of possible actions, ranks opportunities by potential ROI, and applies deterministic safety guardrails before initiating permitted recovery actions through **Razorpay Test Mode**. Every action is verified through payment events and recorded in an auditable trail, while the dashboard measures the actual revenue recovered.

---

## 📌 The Core Problem & The RevoFlow Innovation

### The Traditional Problem:
Most payment recovery tools simply retry checkout payment failures using static timers. However, modern merchants leak massive amounts of revenue across **multiple lifecycle vectors**:
1. **Partial Payments**: Token/advance paid (e.g. ₹4,000 on ₹10,000 order), but the remaining balance is abandoned.
2. **Overdue Invoices**: Enterprise B2B SaaS invoices past due date without automated follow-ups.
3. **Failed Checkout Payments**: Latency timeouts and 3DS OTP drop-offs.

### The Key Question Answered by RevoFlow:
> **"Which revenue opportunity should the merchant recover first to maximize expected recovered revenue?"**

---

## 🔄 The 8-Stage Architecture Pipeline

$$\Large \text{Detect} \longrightarrow \text{Predict} \longrightarrow \text{Calculate} \longrightarrow \text{Prioritize} \longrightarrow \text{Guard} \longrightarrow \text{Recover} \longrightarrow \text{Verify} \longrightarrow \text{Measure}$$

```
Merchant / Razorpay Business Data
        ↓
1. Opportunity Detection (Partials, Overdue Invoices, Checkout Failures)
        ↓
2. ML Recovery Probability Scorer (Calibrated RandomForest Model)
        ↓
3. Expected Value (EV) Formulation:
   EV = (P_recovery × Recoverable Amount) − Action Cost
        ↓
4. Prioritization Matrix (Ranked by Highest Expected Financial ROI)
        ↓
5. Deterministic Guardrails Check (Spend Cap, Cooldown, Fraud Deny-List)
        ↓
6. One-Click Recovery Action (Razorpay Test Mode Dynamic Payment Links)
        ↓
7. Verification & Immutable Audit Trail (Ledger Sync)
        ↓
8. Real-Time Merchant Dashboard (Revenue at Risk, Predicted EV, Settled ₹)
```

---

## 🎯 The 3 Core MVP Revenue Vectors

| Vector | Real-World Scenario | RevoFlow Action | Expected ROI |
| :--- | :--- | :--- | :--- |
| **① Partial Payments** | Customer paid ₹4,000 token on ₹10,000 order; ₹6,000 balance pending. | Generates dynamic Razorpay Balance Payment Link. | **High (~78% Probability)** |
| **② Overdue Invoices** | B2B enterprise SaaS invoice of ₹18,500 is 8 days overdue. | 1-Click WhatsApp / UPI Deep-link with dynamic schedule. | **High (~72% Probability)** |
| **③ Failed Checkouts** | ₹4,999 UPI switch timeout or 3DS OTP abandonment. | Smart delayed retry with 15m cooldown backoff or fallback route. | **High (~84% Probability)** |
| *(Stretch) Reconciliation* | ₹5,200 authorized funds uncaptured nearing 5-day TTL window. | Auto-captures authorized charge and reconciles rail. | **Moderate (~65% Probability)** |

---

## 🧠 Mathematical Expected Value & Prioritization Matrix

To maximize merchant cash flow, RevoFlow evaluates every candidate action across every opportunity using:

$$\text{Expected Value (EV)} = \big( P_{\text{ML}}(\text{action}) \times \text{Recoverable Amount} \big) - \text{Cost}(\text{action})$$

- **Rank #1**: Top financial return (e.g. ₹18,500 overdue invoice @ 72% $\rightarrow$ EV: **₹13,315.00**).
- **De-prioritized**: Low-yield cases (e.g. ₹850 Insufficient funds @ 12% $\rightarrow$ EV: **₹97.00**).

---

## 🛡️ Deterministic Safety Guardrails

To prevent financial loss, customer annoyance, or chargebacks:
1. **Spend Cap (≤ ₹25,000)**: High-value recoveries above ₹25k require human-in-the-loop merchant approval.
2. **Fraud Deny-List**: Customers with `HIGH` fraud risk scores are quarantined immediately.
3. **Attempt Limits**: Maximum 3 attempts per opportunity.
4. **Mandatory Cooldowns**: Enforces 15-minute delays to prevent gateway flooding.

---

## 📊 Live Dashboard Metrics (The Executive Ribbon)

- 🔴 **Revenue at Risk**: Total identified potential loss pool.
- 🟡 **Predicted Recoverable (EV Pool)**: Sum of all machine-learned Expected Values.
- 🟢 **Actual Recovered Revenue**: Verified, settled revenue collected via Razorpay Test Mode.
- 🔵 **Recovery Rate %**: Calculated dynamically in real time:
  $$\text{Recovery Rate} = \left( \frac{\text{Actual Recovered Revenue}}{\text{Revenue at Risk}} \right) \times 100$$

---

## ⚡ Quick Start & Installation

### 1. Install Dependencies
```bash
py -m pip install fastapi uvicorn sqlalchemy pydantic scikit-learn joblib
```

### 2. Seed Database & Train ML Model
```bash
py backend/ml/train.py
py backend/generate_opportunities_data.py
```

### 3. Run the RevoFlow Server
```bash
py -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### 4. Open the Dashboard
Open **http://127.0.0.1:8000/** in your browser to view the live dashboard and execute 1-click recoveries!

---

## 📡 API Endpoints

- **`GET /stats`**: Executive financial summary (Revenue at Risk, Predicted EV, Recovered ₹, Recovery Rate %).
- **`GET /opportunities`**: Prioritized list of revenue opportunities with filtering.
- **`POST /opportunities/{id}/recover`**: Executes 1-click Razorpay recovery link generation.
- **`POST /opportunities/simulate`**: Injects test opportunities across all 3 MVP vectors on the fly.
- **`POST /predict-recovery`**: ML inference API returning probability and EV scores.
- **`GET /docs`**: Interactive Swagger API documentation.

---

## 👥 Authors
Built for the **Razorpay AI Hackathon (Track 3: AI Revenue Recovery)**.