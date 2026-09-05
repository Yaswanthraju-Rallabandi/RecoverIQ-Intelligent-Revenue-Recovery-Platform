import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
from engine.ai_explainer import generate_ai_explanation
from payments.razorpay_client import razorpay_client
from payments.webhook_handler import process_razorpay_webhook

def run_day6_day7_tests():
    print("=" * 70)
    print(">>> RecoverIQ -- DAYS 6 & 7 VERIFICATION SUITE")
    print("=" * 70)

    db = SessionLocal()

    # 1. Day 6: AI Explanation Layer & Confidence-Gating Test
    print("\n[1] Testing Day 6: AI Explanation Layer & Confidence-Gated Review:")
    
    # Normal Opportunity
    normal_opp = {
        "opportunity_type": "partial_payment",
        "recoverable_amount": 6000.0,
        "paid_amount": 4000.0,
        "recovery_probability": 78.5,
        "payment_method": "upi",
        "bank": "HDFC Bank",
        "age_days": 2,
        "customer_risk_score": "LOW",
        "retry_count": 0
    }
    exp_normal = generate_ai_explanation(normal_opp)
    print(f"    - Normal Partial Payment:")
    print(f"      Why Flagged: {exp_normal.why_flagged}")
    print(f"      Why Action:  {exp_normal.why_action_recommended}")
    print(f"      Confidence:  {exp_normal.confidence_score}% [{exp_normal.confidence_tier}] | Gated: {exp_normal.is_confidence_gated}")
    assert not exp_normal.is_confidence_gated, "Normal opportunity should NOT be confidence-gated"

    # High-Value + Low Confidence Opportunity (Confidence-Gating Triggered!)
    risky_high_val = {
        "opportunity_type": "overdue_payment",
        "recoverable_amount": 35000.0, # > Rs 10,000 threshold
        "recovery_probability": 30.0,
        "payment_method": "netbanking",
        "bank": "SBI",
        "age_days": 18,               # Aged -> low confidence
        "customer_risk_score": "HIGH", # High risk -> low confidence
        "retry_count": 2
    }
    exp_gated = generate_ai_explanation(risky_high_val)
    print(f"\n    - High-Value + Low-Confidence Opportunity:")
    print(f"      Confidence: {exp_gated.confidence_score}% [{exp_gated.confidence_tier}]")
    print(f"      Is Gated:   {exp_gated.is_confidence_gated} (Gating Reason: {exp_gated.gating_reason})")
    assert exp_gated.is_confidence_gated, "High-value low-confidence opportunity MUST be confidence-gated to MANUAL_REVIEW!"
    print("    [PASSED] AI Explanation & Confidence-Gating verified!")

    # 2. Day 7: Razorpay Test Mode Payment Link Creation
    print("\n[2] Testing Day 7: Razorpay Test Mode Link Generation:")
    rzp_link = razorpay_client.create_payment_link(
        amount=6000.0,
        reference_id="OPP_PARTIAL_TEST",
        description="Test Razorpay Balance Link"
    )
    print(f"    - Created Razorpay Link: ID = {rzp_link['id']}")
    print(f"    - URL: {rzp_link['short_url']} (Amount: Rs {rzp_link['amount']:,.2f} = {rzp_link['amount_paise']} paise)")
    assert rzp_link["id"].startswith("plink_rzp_"), "Link ID must follow Razorpay schema"
    print("    [PASSED] Razorpay Test Mode Payment Link creation verified.")

    # 3. Day 7: Webhook Ingestion & Strict Idempotency Verification
    print("\n[3] Testing Day 7: Webhook Callback Ingestion & Strict Idempotency Protection:")
    opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.status != "RECOVERED").first()
    assert opp is not None, "Need at least one open opportunity for webhook test"
    
    test_event_id = f"evt_test_idemp_{int(opp.recoverable_amount)}"
    webhook_payload = {
        "opportunity_id": opp.id,
        "amount": opp.recoverable_amount,
        "payment_id": "pay_rzp_hook_101"
    }

    # Call 1: First time webhook fires -> MUST succeed
    success1, msg1, _ = process_razorpay_webhook(db, test_event_id, "payment_link.paid", webhook_payload)
    print(f"    - Webhook Call #1: Success = {success1} | Message: {msg1}")
    assert success1, "First webhook delivery must succeed!"

    # Call 2: Duplicate delivery of SAME webhook event_id -> MUST be rejected by idempotency check
    success2, msg2, details2 = process_razorpay_webhook(db, test_event_id, "payment_link.paid", webhook_payload)
    print(f"    - Webhook Call #2 (Duplicate): Success = {success2} | Message: {msg2}")
    assert not success2 and details2.get("duplicate") is True, "Duplicate webhook MUST be caught and rejected by idempotency key!"
    print("    [PASSED] Webhook idempotency protection verified with 100% precision (Zero double-counting).")

    db.close()
    print("\n" + "=" * 70)
    print("[SUCCESS] ALL DAY 6 & DAY 7 MODULES VERIFIED WITH 100% PRECISION!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_day6_day7_tests()