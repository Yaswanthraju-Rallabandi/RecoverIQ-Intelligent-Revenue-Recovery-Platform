from typing import Dict, Any, NamedTuple, Optional
import os

class AIExplanation(NamedTuple):
    why_flagged: str
    why_action_recommended: str
    confidence_score: float # 0.0 to 100.0%
    confidence_tier: str    # 'HIGH', 'MEDIUM', 'LOW'
    risk_factors: list
    is_confidence_gated: bool
    gating_reason: Optional[str]

def generate_ai_explanation(
    opportunity_dict: Dict[str, Any],
    high_value_threshold: float = 10000.0,
    low_confidence_threshold: float = 60.0
) -> AIExplanation:
    """
    Generates a clear plain-language merchant explanation for why the opportunity was flagged
    and why the specific action was selected.
    
    IMPORTANT: Generated AFTER the deterministic decision is made.
    Confidence-Gating Rule: If confidence < 60% AND amount > Rs 10,000 -> Route to MANUAL_REVIEW.
    """
    opp_type = opportunity_dict.get("opportunity_type", "failed_payment")
    amount = float(opportunity_dict.get("recoverable_amount", 0.0))
    prob = float(opportunity_dict.get("recovery_probability", 50.0))
    method = opportunity_dict.get("payment_method", "upi")
    bank = opportunity_dict.get("bank", "HDFC Bank")
    age_days = int(opportunity_dict.get("age_days", 1))
    risk_score = opportunity_dict.get("customer_risk_score", "LOW")
    retry_count = int(opportunity_dict.get("retry_count", 0))

    risk_factors = []

    # 1. Generate Plain-Language Root-Cause Explanation (Why it was flagged)
    if opp_type == "failed_payment":
        why_flagged = (
            f"A checkout payment of Rs {amount:,.2f} via {bank} ({method.upper()}) failed due to a transient "
            f"gateway switch latency timeout during customer intent authorization."
        )
    elif opp_type == "partial_payment":
        paid = float(opportunity_dict.get("paid_amount", 0.0))
        why_flagged = (
            f"Customer authorized an initial advance token of Rs {paid:,.2f}, but the remaining balance of "
            f"Rs {amount:,.2f} was abandoned {age_days} days ago."
        )
    elif opp_type == "overdue_payment":
        why_flagged = (
            f"High-value B2B SaaS invoice/mandate of Rs {amount:,.2f} is currently {age_days} days overdue past "
            f"the standard net settlement terms."
        )
    else: # refund_mismatch
        why_flagged = (
            f"Pre-authorized charge of Rs {amount:,.2f} was authorized by {bank} but was not captured by the "
            f"merchant backend before the 5-day gateway TTL window."
        )

    # 2. Generate Action Rationale (Why this action was recommended)
    if opp_type == "failed_payment":
        why_recommended = (
            f"Our ML model predicts a {prob}% recovery likelihood upon switch buffer clearance. "
            f"Recommended: Smart Delayed Retry with a 15-minute cooldown to avoid bank rate limits."
        )
    elif opp_type == "partial_payment":
        why_recommended = (
            f"Because the customer already showed high purchase intent by paying the initial deposit, "
            f"dispatching a 1-click Razorpay Balance Link via WhatsApp yields an optimal Expected Value."
        )
    elif opp_type == "overdue_payment":
        why_recommended = (
            f"Customer has a verified past completion history. Sending a frictionless 1-Click UPI Deep-link "
            f"provides an immediate payment schedule without debt collection friction."
        )
    else:
        why_recommended = (
            f"Directly executing an automated gateway pre-auth capture call recovers 100% of the funds "
            f"before the authorization expires at zero friction to the customer."
        )

    # 3. Calculate AI Explanation Confidence Score
    confidence = 85.0
    if age_days > 7:
        confidence -= (age_days * 2.0)
        risk_factors.append(f"Opportunity aging ({age_days} days overdue)")
    if retry_count > 1:
        confidence -= 15.0
        risk_factors.append(f"Multiple previous failed retries ({retry_count})")
    if risk_score == "HIGH":
        confidence -= 30.0
        risk_factors.append("Customer flagged with HIGH risk rating")
    if amount > 20000.0:
        confidence -= 10.0
        risk_factors.append(f"High-value transaction amount (Rs {amount:,.2f})")

    confidence = max(20.0, min(95.0, round(confidence, 1)))
    tier = "HIGH" if confidence >= 75.0 else ("MEDIUM" if confidence >= 60.0 else "LOW")

    # 4. Confidence-Gating Rule Evaluation
    is_gated = False
    gating_reason = None
    if confidence < low_confidence_threshold and amount > high_value_threshold:
        is_gated = True
        gating_reason = (
            f"Confidence-Gating Triggered: High-value opportunity (Rs {amount:,.2f} > Rs {high_value_threshold:,.2f}) "
            f"with low explanation confidence ({confidence}% < {low_confidence_threshold}%). Routed for human sign-off."
        )

    return AIExplanation(
        why_flagged=why_flagged,
        why_action_recommended=why_recommended,
        confidence_score=confidence,
        confidence_tier=tier,
        risk_factors=risk_factors,
        is_confidence_gated=is_gated,
        gating_reason=gating_reason
    )