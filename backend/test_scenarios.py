import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone
from engine.decision_engine import decide_best_recovery_action, ActionType

def run_handpicked_tests():
    print("=" * 70)
    print(">>> DAY 2: DECISION ENGINE & GUARDRAILS - HAND-PICKED SCENARIOS")
    print("=" * 70)

    scenarios = [
        {
            "name": "Scenario 1: Happy Path Timeout (PAY_1021)",
            "payment": {
                "id": "PAY_1021",
                "amount": 4999.00,
                "method": "upi",
                "bank": "HDFC Bank",
                "failure_code": "GATEWAY_TIMEOUT",
                "retry_count": 0,
                "customer_risk_score": "LOW",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=20)
            },
            "bank_status": "HEALTHY",
            "expected_action": ActionType.RETRY_LATER,
            "expected_guardrail": "PASSED"
        },
        {
            "name": "Scenario 2: Retry Limit Hit (Attempt 3 used)",
            "payment": {
                "id": "PAY_EDGE_01",
                "amount": 3500.00,
                "method": "card",
                "bank": "ICICI Bank",
                "failure_code": "GATEWAY_TIMEOUT",
                "retry_count": 3,
                "customer_risk_score": "LOW",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=45)
            },
            "bank_status": "HEALTHY",
            "expected_action": ActionType.MANUAL_REVIEW,
            "expected_guardrail": "BLOCKED"
        },
        {
            "name": "Scenario 3: Cooldown Violation (Retried 2 minutes ago)",
            "payment": {
                "id": "PAY_EDGE_02",
                "amount": 1200.00,
                "method": "upi",
                "bank": "Axis Bank",
                "failure_code": "GATEWAY_TIMEOUT",
                "retry_count": 1,
                "customer_risk_score": "LOW",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=2)
            },
            "bank_status": "HEALTHY",
            "expected_action": ActionType.RETRY_LATER,
            "expected_guardrail": "PASSED"
        },
        {
            "name": "Scenario 4: High-Value Amount Cap Exceeded (Rs 75,000 > Rs 25,000 cap)",
            "payment": {
                "id": "PAY_EDGE_03",
                "amount": 75000.00,
                "method": "netbanking",
                "bank": "HDFC Bank",
                "failure_code": "BANK_DOWN",
                "retry_count": 0,
                "customer_risk_score": "LOW",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=30)
            },
            "bank_status": "HEALTHY",
            "expected_action": ActionType.MANUAL_REVIEW,
            "expected_guardrail": "BLOCKED"
        },
        {
            "name": "Scenario 5: Deny-List / High Risk Fraud Customer",
            "payment": {
                "id": "PAY_EDGE_04",
                "amount": 4500.00,
                "method": "card",
                "bank": "SBI",
                "failure_code": "AUTHENTICATION_FAILED",
                "retry_count": 0,
                "customer_risk_score": "HIGH",
                "is_threat_flagged": True,
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=10)
            },
            "bank_status": "HEALTHY",
            "expected_action": ActionType.MANUAL_REVIEW,
            "expected_guardrail": "BLOCKED"
        },
        {
            "name": "Scenario 6: Issuer Bank Core Switch is DOWN (Circuit Breaker)",
            "payment": {
                "id": "PAY_EDGE_05",
                "amount": 2500.00,
                "method": "upi",
                "bank": "SBI",
                "failure_code": "BANK_DOWN",
                "retry_count": 0,
                "customer_risk_score": "LOW",
                "updated_at": datetime.now(timezone.utc) - timedelta(minutes=15)
            },
            "bank_status": "DOWN",
            "expected_action": ActionType.RECOVERY_LINK,
            "expected_guardrail": "PASSED"
        }
    ]

    all_passed = True

    for idx, sc in enumerate(scenarios, 1):
        print(f"\n[{idx}] {sc['name']}")
        p = sc["payment"]
        print(f"   Input: Rs {p['amount']:,.2f} via {p['bank']} ({p['method']}) | Error: {p['failure_code']} | Retries: {p['retry_count']}")
        
        res = decide_best_recovery_action(p, bank_status=sc["bank_status"])
        
        print(f"   => Chosen Action: {res.chosen_action.value} ('{res.chosen_action_label}')")
        print(f"   => Guardrail Status: {res.guardrail_status}")
        print(f"   => Expected Value: Rs {res.expected_value:,.2f} (Prob: {res.probability}%)")
        print(f"   => Rationale: {res.routing_reason}")

        action_ok = (res.chosen_action == sc["expected_action"])
        guard_ok = (res.guardrail_status == sc["expected_guardrail"])

        if action_ok and guard_ok:
            print("   [TEST RESULT]: PASSED [OK]")
        else:
            print(f"   [TEST RESULT]: FAILED [X] (Expected {sc['expected_action'].value}, got {res.chosen_action.value})")
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] All 6 hand-picked Day 2 scenarios passed with 100% precision!")
    else:
        print("[FAIL] Some scenarios did not match expectations.")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    run_handpicked_tests()