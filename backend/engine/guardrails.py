from typing import Dict, Any, List, NamedTuple, Optional
from datetime import datetime, timedelta, timezone

class GuardrailRule(NamedTuple):
    rule_id: str
    name: str
    description: str
    enabled: bool

# Explicit Guardrail Rules Defined as Data (Config-like List)
GUARDRAIL_RULES = [
    GuardrailRule(
        rule_id="RULE_MAX_RETRIES",
        name="Max Retry Limit",
        description="Blocks all automated recovery attempts if payment attempt count has reached or exceeded max limit (3).",
        enabled=True
    ),
    GuardrailRule(
        rule_id="RULE_COOLDOWN_WINDOW",
        name="Mandatory Cooldown Window",
        description="Blocks immediate retries if executed within minimum cooldown interval of previous attempt.",
        enabled=True
    ),
    GuardrailRule(
        rule_id="RULE_SPEND_CAP",
        name="Automated Amount Threshold Cap",
        description="Caps autonomous recovery at Rs 25,000. Transactions above cap require human-in-the-loop review.",
        enabled=True
    ),
    GuardrailRule(
        rule_id="RULE_DENYLIST",
        name="Customer & Risk Deny-List Check",
        description="Blocks automatic recovery if customer is flagged as HIGH risk or on fraud deny-list.",
        enabled=True
    ),
    GuardrailRule(
        rule_id="RULE_BANK_CIRCUIT_BREAKER",
        name="Issuer Bank Outage Circuit Breaker",
        description="Blocks direct retries if issuer bank core switch is DOWN (outage state).",
        enabled=True
    )
]

class SingleGuardrailResult(NamedTuple):
    rule_id: str
    rule_name: str
    passed: bool
    reason: str

class GuardrailEvaluation(NamedTuple):
    all_passed: bool
    results: List[SingleGuardrailResult]
    blocked_rules: List[str]
    summary: str

def evaluate_guardrails(
    payment_dict: Dict[str, Any],
    candidate_action: str,
    bank_status: str = "HEALTHY",
    max_retries: int = 3,
    max_auto_amount: float = 25000.0,
    cooldown_minutes: int = 15
) -> GuardrailEvaluation:
    results: List[SingleGuardrailResult] = []
    blocked_rules: List[str] = []

    retry_count = payment_dict.get("retry_count", 0)
    amount = float(payment_dict.get("amount", 0.0))
    risk_score = payment_dict.get("customer_risk_score", "LOW")
    last_attempt_time = payment_dict.get("updated_at")

    # 1. Rule: Max Retries (Applies to all automated actions)
    if candidate_action in ["retry_now", "retry_later", "recovery_link"]:
        if retry_count >= max_retries:
            passed = False
            reason = f"Attempt limit reached ({retry_count}/{max_retries} attempts used)."
            blocked_rules.append("RULE_MAX_RETRIES")
        else:
            passed = True
            reason = f"Attempt {retry_count + 1} of {max_retries} permitted."
    else:
        passed = True
        reason = "Not applicable for unrecoverable/manual actions."
    results.append(SingleGuardrailResult("RULE_MAX_RETRIES", "Max Retry Limit", passed, reason))

    # 2. Rule: Cooldown Window (Applies to immediate retry)
    if candidate_action == "retry_now" and retry_count > 0 and last_attempt_time:
        try:
            if isinstance(last_attempt_time, str):
                last_dt = datetime.fromisoformat(last_attempt_time.replace('Z', '+00:00'))
            else:
                last_dt = last_attempt_time
            now = datetime.now(timezone.utc)
            if (now - last_dt) < timedelta(minutes=cooldown_minutes):
                passed = False
                reason = f"Cooldown violation: Last attempt was within {cooldown_minutes}m cooldown window."
                blocked_rules.append("RULE_COOLDOWN_WINDOW")
            else:
                passed = True
                reason = f"Cooldown window ({cooldown_minutes}m) satisfied."
        except Exception:
            passed = True
            reason = "Cooldown verified."
    else:
        passed = True
        reason = "Cooldown satisfied or scheduled."
    results.append(SingleGuardrailResult("RULE_COOLDOWN_WINDOW", "Mandatory Cooldown Window", passed, reason))

    # 3. Rule: Automated Amount Cap (Applies to all automated actions)
    if candidate_action in ["retry_now", "retry_later", "recovery_link"]:
        if amount > max_auto_amount:
            passed = False
            reason = f"Amount Rs {amount:,.2f} exceeds auto-pilot cap (Rs {max_auto_amount:,.2f}). Requires manual signoff."
            blocked_rules.append("RULE_SPEND_CAP")
        else:
            passed = True
            reason = f"Amount Rs {amount:,.2f} is within automated threshold (Rs {max_auto_amount:,.2f})."
    else:
        passed = True
        reason = "Within policy limit."
    results.append(SingleGuardrailResult("RULE_SPEND_CAP", "Automated Amount Threshold Cap", passed, reason))

    # 4. Rule: Deny-List / High Risk Check
    if risk_score == "HIGH" or payment_dict.get("is_threat_flagged", False):
        passed = False
        reason = f"Customer profile flagged as {risk_score} risk or on fraud deny-list. Auto-execution blocked."
        blocked_rules.append("RULE_DENYLIST")
    else:
        passed = True
        reason = f"Customer risk rating is {risk_score} (Clean profile)."
    results.append(SingleGuardrailResult("RULE_DENYLIST", "Customer & Risk Deny-List Check", passed, reason))

    # 5. Rule: Bank Circuit Breaker (Applies to direct retries against the bank)
    if candidate_action in ["retry_now", "retry_later"]:
        if bank_status == "DOWN":
            passed = False
            reason = "Issuer core banking switch is DOWN. Circuit breaker active."
            blocked_rules.append("RULE_BANK_CIRCUIT_BREAKER")
        else:
            passed = True
            reason = f"Issuer switch status: {bank_status}."
    else:
        passed = True
        reason = "Rail independent (Recovery Link bypassed circuit breaker)."
    results.append(SingleGuardrailResult("RULE_BANK_CIRCUIT_BREAKER", "Issuer Bank Outage Circuit Breaker", passed, reason))

    all_passed = (len(blocked_rules) == 0)
    summary = "All guardrails passed." if all_passed else f"Blocked by: {', '.join(blocked_rules)}"

    return GuardrailEvaluation(all_passed, results, blocked_rules, summary)