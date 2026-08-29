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
    Deterministic Safety Guardrail Policies:
    1. Spend Cap: Maximum Rs 25,000 for autonomous action. High value -> Manual Review.
    2. Fraud / Blocked Accounts: Quarantined immediately.
    3. Retry Limit: Max 3 attempts per opportunity.
    """
    blocked_reasons = []

    # Rule 1: Fraud / Blocked Account Check
    if is_blacklisted or risk_score == "HIGH":
        blocked_reasons.append("Customer flagged with HIGH risk rating or on fraud deny-list.")

    # Rule 2: Spend Cap
    if amount > spend_cap:
        blocked_reasons.append(f"Amount Rs {amount:,.2f} exceeds auto-pilot cap (Rs {spend_cap:,.2f}). Requires human approval.")

    # Rule 3: Max Retries
    if retry_count >= max_retries:
        blocked_reasons.append(f"Attempt limit reached ({retry_count}/{max_retries} attempts used).")

    all_passed = (len(blocked_reasons) == 0)
    summary = "All safety guardrails passed." if all_passed else " | ".join(blocked_reasons)

    return {
        "all_passed": all_passed,
        "blocked_reasons": blocked_reasons,
        "summary": summary
    }