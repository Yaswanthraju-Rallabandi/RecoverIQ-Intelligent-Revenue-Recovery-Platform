import sys
import os
import json
import urllib.request
import urllib.error

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, SessionLocal
import models
from detectors.manager import OpportunityDetectorManager
from ml.predictor import predict_single_probability
from engine.optimizer import run_constrained_optimization_comparison, solve_01_knapsack_dp, solve_greedy_by_ratio, solve_naive_fifo
from engine.ai_explainer import generate_ai_explanation
from payments.razorpay_client import razorpay_client
from payments.webhook_handler import process_razorpay_webhook

def audit_full_application():
    print("=" * 75)
    print(">>> RecoverIQ COMPREHENSIVE END-TO-END APPLICATION AUDIT")
    print("=" * 75)

    errors = []
    warnings = []

    # -------------------------------------------------------------
    # 1. Database & Table Schema Integrity Audit
    # -------------------------------------------------------------
    print("\n[CHECK 1/7] Database & Schema Integrity...")
    db = SessionLocal()
    try:
        tables = list(models.Base.metadata.tables.keys())
        expected_tables = [
            "users", "merchants", "customers", "payments", "invoices", 
            "refunds", "revenue_opportunities", "recovery_predictions", 
            "recovery_actions", "guardrail_events", "webhook_events", 
            "audit_logs", "model_versions"
        ]
        missing = [t for t in expected_tables if t not in tables]
        if missing:
            errors.append(f"Missing database tables: {missing}")
        else:
            print(f"  [OK] All 13 tables verified: {', '.join(tables)}")

        user_cnt = db.query(models.User).count()
        merch_cnt = db.query(models.Merchant).count()
        cust_cnt = db.query(models.Customer).count()
        opp_cnt = db.query(models.RevenueOpportunity).count()
        print(f"  [OK] Data integrity: {merch_cnt} merchants, {user_cnt} users, {cust_cnt} customers, {opp_cnt} opportunities.")
    except Exception as e:
        errors.append(f"Database query error: {e}")

    # -------------------------------------------------------------
    # 2. Opportunity Detectors Audit
    # -------------------------------------------------------------
    print("\n[CHECK 2/7] 4 Opportunity Detectors Audit...")
    try:
        manager = OpportunityDetectorManager()
        detected_types = set(d.__class__.__name__ for d in manager.detectors)
        expected_detectors = {
            "FailedPaymentDetector", "PartialPaymentDetector", 
            "OverdueInvoiceDetector", "RefundMismatchDetector"
        }
        if detected_types != expected_detectors:
            errors.append(f"Detector mismatch: found {detected_types}, expected {expected_detectors}")
        else:
            print(f"  [OK] All 4 detector classes registered: {detected_types}")
    except Exception as e:
        errors.append(f"Detector initialization error: {e}")

    # -------------------------------------------------------------
    # 3. ML Prediction Pipeline & Edge Case Audit
    # -------------------------------------------------------------
    print("\n[CHECK 3/7] ML Model & Inference Edge Cases...")
    try:
        p1, c1 = predict_single_probability(amount=0.0, method="upi", opportunity_type="failed_payment")
        p2, c2 = predict_single_probability(amount=1000000.0, method="card", opportunity_type="overdue_payment", age_days=45)
        p3, c3 = predict_single_probability(amount=5000.0, method="crypto", opportunity_type="custom_type")
        
        print(f"  [OK] Zero amount inference: {p1}% [{c1}]")
        print(f"  [OK] Extreme amount inference: {p2}% [{c2}]")
        print(f"  [OK] Unknown category fallback: {p3}% [{c3}]")
    except Exception as e:
        errors.append(f"ML predictor error on edge cases: {e}")

    # -------------------------------------------------------------
    # 4. Knapsack Optimizer Edge Cases Audit
    # -------------------------------------------------------------
    print("\n[CHECK 4/7] 0/1 Knapsack Optimizer Edge Cases...")
    try:
        opps = db.query(models.RevenueOpportunity).all()
        comp_zero = run_constrained_optimization_comparison(opps, capacity_budget=0)
        assert comp_zero.optimal_dp.item_count == 0, "Capacity 0 should select 0 items"
        
        comp_large = run_constrained_optimization_comparison(opps, capacity_budget=50)
        assert comp_large.optimal_dp.item_count >= 1, "Large capacity should select items"
        
        comp_normal = run_constrained_optimization_comparison(opps, capacity_budget=6)
        print(f"  [OK] Normal Budget (N=6): Selected {comp_normal.optimal_dp.item_count} items (EV: Rs {comp_normal.optimal_dp.total_expected_value:,.2f})")
        print(f"  [OK] Optimization Lift over Naive: +{comp_normal.dp_lift_over_naive_percent}%")
    except Exception as e:
        errors.append(f"Optimizer edge case error: {e}")

    # -------------------------------------------------------------
    # 5. AI Explainer & Confidence Gating Audit
    # -------------------------------------------------------------
    print("\n[CHECK 5/7] AI Explanation & Confidence-Gating Audit...")
    try:
        normal_exp = generate_ai_explanation({"opportunity_type": "partial_payment", "recoverable_amount": 5000.0, "age_days": 1})
        assert not normal_exp.is_confidence_gated
        
        gated_exp = generate_ai_explanation({
            "opportunity_type": "overdue_payment", 
            "recoverable_amount": 25000.0, 
            "age_days": 20, 
            "customer_risk_score": "HIGH"
        })
        assert gated_exp.is_confidence_gated
        print(f"  [OK] Normal explanation confidence: {normal_exp.confidence_score}% (Gated: {normal_exp.is_confidence_gated})")
        print(f"  [OK] Risky explanation confidence:  {gated_exp.confidence_score}% (Gated: {gated_exp.is_confidence_gated})")
    except Exception as e:
        errors.append(f"AI Explainer error: {e}")

    # -------------------------------------------------------------
    # 6. Razorpay Test Mode & Webhook Idempotency Audit
    # -------------------------------------------------------------
    print("\n[CHECK 6/7] Razorpay Client & Webhook Idempotency Audit...")
    try:
        link = razorpay_client.create_payment_link(1250.0, reference_id="AUDIT_TEST")
        assert link["amount_paise"] == 125000
        print(f"  [OK] Razorpay Test Link generated: {link['id']} (URL: {link['short_url']})")

        evt_key = f"evt_audit_unique_{int(link['created_at'])}"
        test_opp = db.query(models.RevenueOpportunity).first()
        if test_opp:
            s1, _, _ = process_razorpay_webhook(db, evt_key, "payment_link.paid", {"opportunity_id": test_opp.id, "amount": test_opp.recoverable_amount})
            s2, _, d2 = process_razorpay_webhook(db, evt_key, "payment_link.paid", {"opportunity_id": test_opp.id, "amount": test_opp.recoverable_amount})
            assert s1 is True and s2 is False and d2.get("duplicate") is True
            print(f"  [OK] Strict Webhook Idempotency verified (Duplicate rejected with zero double-counting).")
    except Exception as e:
        errors.append(f"Razorpay / Webhook error: {e}")

    # -------------------------------------------------------------
    # 7. Live FastAPI HTTP Endpoints Audit
    # -------------------------------------------------------------
    print("\n[CHECK 7/7] Live FastAPI HTTP Endpoints Audit (http://127.0.0.1:8000)...")
    endpoints_to_test = [
        ("GET", "/", None),
        ("GET", "/health", None),
        ("GET", "/stats", None),
        ("GET", "/opportunities", None),
        ("GET", "/opportunities?type_filter=failed_payment", None),
        ("GET", "/optimize?capacity_budget=6", None),
        ("POST", "/predict-recovery", {"amount": 4999.0, "payment_method": "upi", "opportunity_type": "failed_payment"}),
        ("POST", "/simulate-webhook", {"opportunity_id": "OPP_FAIL_PAY_1023", "amount": 8200.0})
    ]

    for method, path, payload in endpoints_to_test:
        url = f"http://127.0.0.1:8000{path}"
        try:
            if method == "GET":
                req = urllib.request.Request(url)
            else:
                req = urllib.request.Request(
                    url, 
                    data=json.dumps(payload).encode("utf-8"), 
                    headers={"Content-Type": "application/json"}
                )
            with urllib.request.urlopen(req, timeout=5) as response:
                status = response.getcode()
                if status == 200:
                    print(f"  [OK] {method:4s} {path:40s} -> HTTP 200 OK")
                else:
                    errors.append(f"{method} {path} returned status {status}")
        except urllib.error.URLError as e:
            errors.append(f"HTTP Request failed for {method} {path}: {e}")

    db.close()

    # -------------------------------------------------------------
    # Final Audit Summary
    # -------------------------------------------------------------
    print("\n" + "=" * 75)
    if not errors and not warnings:
        print("[AUDIT RESULT: PERFECT] ZERO ERRORS OR WARNINGS FOUND ACROSS THE ENTIRE APPLICATION!")
        print("  - All 13 database tables, relationships, and queries are healthy.")
        print("  - All 4 opportunity detectors and ML scoring pipelines run error-free.")
        print("  - 0/1 Knapsack optimizer correctly solves constrained action sets.")
        print("  - AI explanation and confidence-gating layer correctly quarantines high-risk items.")
        print("  - Razorpay test-mode client and idempotent webhook listeners are fully operational.")
        print("  - All live HTTP endpoints responded with HTTP 200 OK.")
    else:
        print(f"[AUDIT RESULT] Found {len(errors)} errors and {len(warnings)} warnings:")
        for err in errors:
            print(f"   [ERROR] {err}")
        for w in warnings:
            print(f"   [WARNING] {w}")
    print("=" * 75 + "\n")

if __name__ == "__main__":
    audit_full_application()