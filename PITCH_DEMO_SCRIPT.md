#  RecoverIQ — 5-Minute Hackathon Pitch & Video Demo Script
### *Razorpay AI Hackathon (Track 3: AI Revenue Recovery)*
**Project Name**: RecoverIQ — AI Revenue Recovery & Optimization Engine  
**Target Duration**: 5:00 Minutes

---

##  Timestamped Narration & Demo Guide

### 0:00 – 0:45 | 1. The Core Problem & Differentiator #1
**Screen**: Show Dashboard headline ribbon (Revenue at Risk vs Recovered).
**Voiceover**:
> *"Hi everyone, I'm Yaswanth Raju, and this is **RecoverIQ** — an autonomous AI Revenue Recovery & Optimization Engine built for Track 3 of the Razorpay AI Hackathon.*
>
> *Most payment recovery tools today make two fatal assumptions:*
> *First, they only look at failed checkout payments, ignoring the massive revenue leaking across partial payments, overdue B2B invoices, and pre-auth reconciliation mismatches.*
> *Second, when merchants have limited daily operational capacity, existing tools either sort by value or retry chronologically.*
>
> *RecoverIQ solves this through our first core differentiator: **Resource-Constrained Optimization**. We don't just sort opportunities. We formulate recovery as an exact **0/1 Knapsack Dynamic Program** that chooses the mathematical combination of actions that maximizes recovered revenue within the merchant's daily capacity budget."*

---

### 0:45 – 1:45 | 2. Multi-Vector Opportunity Detection & ML Scorer
**Screen**: Filter through the 4 detector tabs on the dashboard (`1. Failed Checkouts`, `2. Partial Payments`, `3. Overdue Invoices`, `4. Refund Mismatches`).
**Voiceover**:
> *"RecoverIQ ingests data across four distinct revenue vectors:*
> *1. **Failed Checkouts**: Gateway switch timeouts and 3DS OTP drop-offs.*
> *2. **Partial Payments**: Customers who paid an advance token but abandoned the remaining balance.*
> *3. **Overdue Invoices**: Corporate B2B receivables and recurring mandates past due.*
> *4. **Refund & Pre-Auth Mismatches**: Authorized charges nearing the 5-day capture TTL window.*
>
> *Every opportunity is evaluated by our **Calibrated Random Forest ML Model**, trained with 5-fold Platt scaling on 4,000 ground-truth records. It produces empirical recovery probabilities and calculates Expected Financial Value: EV = (P_recovery * Amount) - Action Cost."*

---

### 1:45 – 2:45 | 3. Differentiator #2: AI Explains, But Code Decides & Guardrails
**Screen**: Click on an opportunity to open the **AI Opportunity Diagnostic Drawer**, then click a high-risk opportunity quarantined in `MANUAL_REVIEW`.
**Voiceover**:
> *"This brings us to our second core differentiator: **The AI-Explains-But-Does-Not-Decide Boundary**.*
>
> *We never allow an LLM or probabilistic model to make financial decisions. In RecoverIQ:*
> - *Deterministic code enforces all safety guardrails: spend caps of Rs 25,000, fraud deny-lists, and cooldown intervals.*
> - *Our AI Explanation Layer generates plain-language root-cause diagnoses and action rationales **after** the deterministic decision is made.*
> - *Furthermore, we built **Confidence-Gated Review**: if an opportunity is above Rs 10,000 and the AI confidence is below 60%, it is automatically quarantined for human merchant sign-off."*

---

### 2:45 – 3:45 | 4. Constrained Knapsack Optimization & Counterfactual Lift
**Screen**: Drag the **Daily Capacity Slider (N)** on the dashboard from 4 to 6 to 10 units. Highlight the Strategy Comparison cards and Counterfactual Lift (+72.8%).
**Voiceover**:
> *"Now let's look at the constrained optimization in action.*
> *Here, the merchant sets a daily capacity budget of 6 effort units.*
> *Notice how RecoverIQ recomputes the optimal subset in real time.*
>
> *If the merchant had used a naive 'Sort by Expected Value' or FIFO approach, they would have recovered Rs 20,433.*
> *By using RecoverIQ's **0/1 Knapsack Dynamic Program**, the system selects the mathematically optimal combination, delivering **Rs 35,306 in expected revenue — a +72.8% lift** within the exact same operational budget!"*

---

### 3:45 – 4:45 | 5. Razorpay Test-Mode Execution & Idempotent Webhooks
**Screen**: Click **"Execute Optimal Action Set (1-Click)"** (triggering confetti and settled revenue update), open a generated `plink_...` test link, and click **"Simulate Webhook Paid"**.
**Voiceover**:
> *"With one click, the merchant can execute the entire optimal action set.*
> *RecoverIQ connects directly to **Razorpay Test Mode APIs**:*
> - *Generating dynamic Razorpay Payment Links for partial balances and overdue invoices.*
> - *Triggering smart payment retries for checkout switch timeouts.*
> - *Executing automated pre-auth captures for gateway reconciliation.*
>
> *When a customer completes payment, Razorpay webhooks fire into our endpoint. Our **Webhook Idempotency Ledger** verifies the signature and event ID, ensuring zero double-execution even if webhooks fire multiple times."*

---

### 4:45 – 5:00 | 6. Conclusion
**Screen**: Show full dashboard with segmented metrics ribbon and audit trail.
**Voiceover**:
> *"In summary, RecoverIQ combines multi-source revenue detection, calibrated machine learning, resource-constrained knapsack optimization, and deterministic safety to turn lost revenue into guaranteed cash flow.*
>
> *Thank you, and we look forward to your questions!"*

---

##  Key Highlight Checklist for Recording:
- [x] **Differentiator 1 Explicitly Stated**: Resource-constrained optimization (not just sorting).
- [x] **Differentiator 2 Explicitly Stated**: AI explains but does not decide (deterministic guardrails).
- [x] All 4 opportunity types shown.
- [x] Knapsack budget slider demonstrated.
- [x] Guardrail quarantine demonstrated.
- [x] 1-Click Razorpay execution & webhook verification shown.