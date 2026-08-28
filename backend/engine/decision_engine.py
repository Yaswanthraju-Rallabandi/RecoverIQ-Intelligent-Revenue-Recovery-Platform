from typing import Dict, Any, List, Tuple, NamedTuple
from datetime import datetime, timezone
from .actions import ActionType, ACTION_REGISTRY, ActionDefinition
from .guardrails import evaluate_guardrails, GuardrailEvaluation

try:
    from ml.predictor import predict_single_probability
except ImportError:
    from backend.ml.predictor import predict_single_probability

class CandidateActionScore(NamedTuple):
    action_type: ActionType
    label: str
    probability: float # 0.0 to 100.0 from ML Model
    cost: float # In INR
    expected_value: float # In INR
    guardrail_eval: GuardrailEvaluation
    is_eligible: bool # Passed guardrails

class DecisionResult(NamedTuple):
    chosen_action: ActionType
    chosen_action_label: str
    expected_value: float
    probability: float
    confidence_level: str
    guardrail_status: str # 'PASSED' or 'BLOCKED'
    all_candidate_scores: List[CandidateActionScore]
    fallback_ranked_actions: List[ActionType]
    routing_reason: str
    model_version: str

def calculate_expected_value(probability: float, amount: float, cost: float) -> float:
    """
    Formula: EV = (Probability / 100 * Amount) - Cost
    """
    raw_ev = (probability / 100.0) * amount - cost
    return max(0.0, round(raw_ev, 2))

def decide_best_recovery_action(
    payment_dict: Dict[str, Any],
    bank_status: str = "HEALTHY"
) -> DecisionResult:
    """
    Day 3 Upgraded Action Selection Pipeline:
    1. Evaluates declarative guardrails for each candidate action.
    2. Runs the trained ML Model to predict genuine recovery probability.
    3. Computes Expected Value (EV) for all candidates.
    4. Filters to only eligible candidates (passed guardrails).
    5. Selects the highest EV action.
    6. If all blocked -> Routes strictly to MANUAL_REVIEW.
    """
    amount = float(payment_dict.get("amount", 0.0))
    failure_code = payment_dict.get("failure_code", "GATEWAY_TIMEOUT")
    method = payment_dict.get("method", "upi")
    retry_count = int(payment_dict.get("retry_count", 0))
    past_success = int(payment_dict.get("past_successful_payments", 4))
    
    # Temporal feature
    now_hour = datetime.now(timezone.utc).hour

    candidate_actions = [
        ActionType.RETRY_LATER,
        ActionType.RETRY_NOW,
        ActionType.RECOVERY_LINK,
        ActionType.UNRECOVERABLE
    ]

    scored_candidates: List[CandidateActionScore] = []

    for action_type in candidate_actions:
        action_def = ACTION_REGISTRY[action_type]
        
        # 1. Guardrail Check FIRST
        guard_eval = evaluate_guardrails(
            payment_dict=payment_dict,
            candidate_action=action_type.value,
            bank_status=bank_status
        )

        # 2. Real ML Model Prediction
        if action_type == ActionType.UNRECOVERABLE:
            prob = 0.0
            conf = "LOW"
        else:
            prob, conf = predict_single_probability(
                amount=amount,
                method=method,
                failure_code=failure_code,
                attempt_number=retry_count + 1,
                hour_of_day=now_hour,
                past_successful_payments=past_success,
                action_type=action_type.value
            )

        cost = action_def.base_cost

        # 3. Expected Value: (P_ml * Amount) - Cost
        ev = calculate_expected_value(prob, amount, cost)

        scored_candidates.append(CandidateActionScore(
            action_type=action_type,
            label=action_def.label,
            probability=prob,
            cost=cost,
            expected_value=ev,
            guardrail_eval=guard_eval,
            is_eligible=guard_eval.all_passed
        ))

    # Filter only eligible actions (passed guardrails) excluding unrecoverable if viable alternatives exist
    eligible = [c for c in scored_candidates if c.is_eligible and c.action_type != ActionType.UNRECOVERABLE]

    if eligible:
        # Sort eligible actions by Expected Value (highest first)
        eligible.sort(key=lambda x: x.expected_value, reverse=True)
        winner = eligible[0]
        
        fallback_ranked = [c.action_type for c in eligible[1:]]
        conf = "HIGH" if (winner.probability >= 70 or winner.probability <= 20) else ("MEDIUM" if winner.probability >= 45 else "LOW")

        return DecisionResult(
            chosen_action=winner.action_type,
            chosen_action_label=winner.label,
            expected_value=winner.expected_value,
            probability=winner.probability,
            confidence_level=conf,
            guardrail_status="PASSED",
            all_candidate_scores=scored_candidates,
            fallback_ranked_actions=fallback_ranked,
            routing_reason=f"ML predicted {winner.probability}% success with highest expected value (Rs {winner.expected_value:,.2f}) and all safety guardrails passed.",
            model_version="v1.0-randomforest-calibrated"
        )
    else:
        # All automatic recovery actions blocked by guardrails -> Strict Route to MANUAL_REVIEW
        manual_def = ACTION_REGISTRY[ActionType.MANUAL_REVIEW]
        
        blocked_reasons = []
        for c in scored_candidates:
            if c.guardrail_eval.blocked_rules:
                blocked_reasons.extend(c.guardrail_eval.blocked_rules)
        blocked_summary = ", ".join(set(blocked_reasons)) if blocked_reasons else "Safety policy constraint"

        return DecisionResult(
            chosen_action=ActionType.MANUAL_REVIEW,
            chosen_action_label=manual_def.label,
            expected_value=0.0,
            probability=0.0,
            confidence_level="LOW",
            guardrail_status="BLOCKED",
            all_candidate_scores=scored_candidates,
            fallback_ranked_actions=[ActionType.UNRECOVERABLE],
            routing_reason=f"All autonomous recovery actions blocked by guardrails ({blocked_summary}). Routed to merchant manual review.",
            model_version="v1.0-randomforest-calibrated"
        )