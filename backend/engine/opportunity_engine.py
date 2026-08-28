from typing import Dict, Any, List, NamedTuple
from datetime import datetime, timezone
import math

class OpportunityTypeInfo(NamedTuple):
    type_code: str
    label: str
    base_recovery_odds: float
    recommended_action: str
    action_type: str
    action_cost: float

OPPORTUNITY_TYPES: Dict[str, OpportunityTypeInfo] = {
    "PARTIAL_PAYMENT": OpportunityTypeInfo(
        type_code="PARTIAL_PAYMENT",
        label="Partial Payment Balance Due",
        base_recovery_odds=78.0,
        recommended_action="Dispatch Razorpay Balance Payment Link via WhatsApp",
        action_type="smart_recovery_link",
        action_cost=5.0
    ),
    "OVERDUE_INVOICE": OpportunityTypeInfo(
        type_code="OVERDUE_INVOICE",
        label="Overdue B2B Invoice / Mandate",
        base_recovery_odds=72.0,
        recommended_action="1-Click UPI Deep-link & Dynamic Payment Schedule",
        action_type="smart_recovery_link",
        action_cost=5.0
    ),
    "REFUND_MISMATCH": OpportunityTypeInfo(
        type_code="REFUND_MISMATCH",
        label="Payment / Refund Reconciliation Glitch",
        base_recovery_odds=65.0,
        recommended_action="Auto-Capture Authorized Funds & Reconcile Rail",
        action_type="gateway_reconcile",
        action_cost=2.0
    ),
    "FAILED_PAYMENT": OpportunityTypeInfo(
        type_code="FAILED_PAYMENT",
        label="Checkout Payment Failure (Timeout / 3DS Drop)",
        base_recovery_odds=84.0,
        recommended_action="Smart Delayed Retry (15m Cooldown Backoff)",
        action_type="smart_retry",
        action_cost=2.0
    )
}

def calculate_opportunity_score(opp_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes calibrated recovery probability, Expected Value (EV),
    and evaluates safety guardrails for any revenue opportunity.
    """
    opp_type = opp_dict.get("opportunity_type", "FAILED_PAYMENT")
    recoverable_amt = float(opp_dict.get("recoverable_amount", 0.0))
    age_days = int(opp_dict.get("age_days", 1))
    risk_score = opp_dict.get("customer_risk_score", "LOW")
    retry_count = int(opp_dict.get("retry_count", 0))
    past_success = int(opp_dict.get("past_successful_payments", 4))
    
    info = OPPORTUNITY_TYPES.get(opp_type, OPPORTUNITY_TYPES["FAILED_PAYMENT"])
    
    # 1. Probability Calculation
    prob = info.base_recovery_odds
    
    # Aging decay: older opportunities have lower recovery odds (-2% per day overdue)
    prob -= (min(age_days, 15) * 2.0)
    
    # Retry penalty: -10% per failed previous attempt
    prob -= (retry_count * 10.0)
    
    # Customer risk modifier
    if risk_score == "LOW":
        prob += 5.0
    elif risk_score == "HIGH":
        prob -= 25.0
        
    # Past completion history trust bonus
    if past_success >= 5:
        prob += 4.0
    elif past_success == 0:
        prob -= 6.0
        
    final_prob = max(5.0, min(95.0, round(prob, 1)))
    
    # 2. Expected Value Formulation: EV = (Probability / 100 * Recoverable Amount) - Action Cost
    ev = max(0.0, round((final_prob / 100.0) * recoverable_amt - info.action_cost, 2))
    
    # 3. Deterministic Safety Guardrails Check
    retry_limit_passed = (retry_count < 3)
    spend_cap_passed = (recoverable_amt <= 25000.0)
    fraud_check_passed = (risk_score != "HIGH")
    all_guardrails_passed = retry_limit_passed and spend_cap_passed and fraud_check_passed
    
    guardrail_status = "PASSED" if all_guardrails_passed else "BLOCKED"
    
    # Recommended action & rationale
    if not all_guardrails_passed:
        action_label = "Escalate for Merchant Manual Review"
        action_type = "manual_review"
        if not spend_cap_passed:
            ai_rationale = f"High-value opportunity (Rs {recoverable_amt:,.2f} > Rs 25,000 threshold). Automated execution held for human-in-the-loop sign-off."
        elif not fraud_check_passed:
            ai_rationale = f"Customer flagged with {risk_score} fraud score. Automated recovery quarantined to prevent chargeback risk."
        else:
            ai_rationale = "Maximum retry attempt limit reached (3/3). Requires manual intervention."
    else:
        action_label = info.recommended_action
        action_type = info.action_type
        ai_rationale = f"Opportunity shows {final_prob}% recovery likelihood with positive Expected Value (Rs {ev:,.2f}). Action: {action_label}."
        
    confidence = "HIGH" if (final_prob >= 70 or final_prob <= 20) else ("MEDIUM" if final_prob >= 45 else "LOW")

    return {
        "recovery_probability": final_prob,
        "confidence_level": confidence,
        "expected_value": ev,
        "recommended_action": action_label,
        "action_type": action_type,
        "action_cost": info.action_cost,
        "guardrail_status": guardrail_status,
        "all_guardrails_passed": all_guardrails_passed,
        "ai_rationale": ai_rationale
    }