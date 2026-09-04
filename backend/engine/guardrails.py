from typing import Dict, Any, NamedTuple, List

def evaluate_guardrails(
    amount: float,
    risk_score: str = "LOW",
    is_blacklisted: bool = False,
    retry_count: int = 0,
    max_retries: int = 3,
    spend_cap: float = 25000.0
) -> Dict[str, Any]:
    """
    General Deterministic Safety Guardrail Policies:
    1. Spend Cap: Maximum Rs 25,000 for autonomous action. High value -> Manual Review.
    2. Fraud / Blocked Accounts: Quarantined immediately.
    3. Retry Limit: Max 3 attempts per opportunity.
    """
    blocked_reasons = []

    # Rule 1: Fraud / Blocked Account Check
    if is_blacklisted or risk_score == "HIGH":
        blocked_reasons.append("Customer flagged with HIGH risk rating or on fraud deny-list.")

    # Rule 2: General Spend Cap
    if amount > spend_cap:
        blocked_reasons.append(f"Amount Rs {amount:,.2f} exceeds auto-pilot cap (Rs {spend_cap:,.2f}). Requires human approval.")

    # Rule 3: Max Retries
    if retry_count >= max_retries:
        blocked_reasons.append(f"Attempt limit reached ({retry_count}/{max_retries} attempts used).")

    all_passed = (len(blocked_reasons) == 0)
    summary = "All general safety guardrails passed." if all_passed else " | ".join(blocked_reasons)

    return {
        "all_passed": all_passed,
        "blocked_reasons": blocked_reasons,
        "summary": summary
    }

def evaluate_preauth_capture_guardrail(
    amount: float,
    auth_age_hours: float = 36.0,
    risk_score: str = "LOW",
    has_chargeback_history: bool = False,
    preauth_spend_cap: float = 7500.0
) -> Dict[str, Any]:
    """
    Dedicated Pre-Auth Auto-Capture Guardrail Policy (Senior Risk Control):
    Unlike payment links (which require customer action), pre-auth capture moves money
    unilaterally from the cardholder's reserved balance. Hence it is subject to stricter policies:
    
    1. Dedicated Auto-Capture Cap: Capped at Rs 7,500 (lower than the general Rs 25k cap).
    2. Grace Period Window: Minimum 24 hours must have elapsed to prevent capturing cancelled orders.
    3. TTL Safety Ceiling: Must not exceed 110 hours (within 120-hour / 5-day bank TTL).
    4. Chargeback / Dispute Quarantine: Never auto-capture if cardholder has open disputes.
    """
    restrictions = []

    # Strict Policy 1: Pre-Auth Auto-Capture Cap (Rs 7,500)
    if amount > preauth_spend_cap:
        restrictions.append(f"Pre-auth auto-capture amount (Rs {amount:,.2f}) exceeds dedicated auto-capture ceiling of Rs {preauth_spend_cap:,.2f}. Quarantined for Merchant Manual Sign-off.")

    # Strict Policy 2: Minimum 24h Cooling Buffer
    if auth_age_hours < 24.0:
        restrictions.append(f"Pre-auth age ({auth_age_hours:.1f}h) is under the 24-hour dispute/cancellation cooling buffer. Auto-capture withheld.")

    # Strict Policy 3: Maximum 110h TTL Window
    if auth_age_hours > 110.0:
        restrictions.append(f"Pre-auth age ({auth_age_hours:.1f}h) is nearing critical 120h bank TTL. Requires urgent manual verification before capture.")

    # Strict Policy 4: Chargeback / Risk check
    if has_chargeback_history or risk_score in ["HIGH", "MEDIUM_HIGH"]:
        restrictions.append("Cardholder profile flagged with dispute history. Unilateral pre-auth capture blocked.")

    allowed = (len(restrictions) == 0)
    return {
        "allowed_autonomous_capture": allowed,
        "guardrail_status": "PASSED" if allowed else "MANUAL_REVIEW",
        "guardrail_code": "PREAUTH_AUTONOMOUS_APPROVED" if allowed else "GUARDRAIL_PREAUTH_AUTO_CAPTURE_RESTRICTED",
        "restrictions": restrictions,
        "rationale": "Autonomous pre-auth capture safely permitted within Rs 7,500 threshold and 24-110h window." if allowed else " | ".join(restrictions)
    }