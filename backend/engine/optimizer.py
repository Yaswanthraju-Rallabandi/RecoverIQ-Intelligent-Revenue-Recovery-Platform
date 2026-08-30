from typing import List, Dict, Any, Tuple, NamedTuple
import math

class OptimizationItem(NamedTuple):
    id: str
    title: str
    opportunity_type: str
    customer_name: str
    recoverable_amount: float
    recovery_probability: float
    expected_value: float # Value V_i
    weight: int          # Operational effort / cost W_i (integer scale for DP)
    raw_cost: float
    recommended_action: str
    guardrail_status: str

class StrategyResult(NamedTuple):
    strategy_name: str
    selected_items: List[Dict[str, Any]]
    total_expected_value: float
    total_recoverable_amount: float
    total_weight_used: int
    capacity_limit: int
    item_count: int
    efficiency_ratio: float # EV per unit weight

class OptimizationComparison(NamedTuple):
    optimal_dp: StrategyResult
    greedy_ratio: StrategyResult
    naive_fifo: StrategyResult
    capacity_budget: int
    total_opportunities_evaluated: int
    dp_lift_over_naive_percent: float
    dp_lift_over_greedy_percent: float

def prepare_items_from_opportunities(opps: List[Any]) -> List[OptimizationItem]:
    """
    Transforms database opportunities into optimization items with integer weights.
    Weight represents operational effort/cost:
    - failed_payment (automated retry): weight = 1 (effort = 1 unit)
    - refund_mismatch (API capture): weight = 1 (effort = 1 unit)
    - partial_payment (custom balance link): weight = 2 (effort = 2 units)
    - overdue_payment (B2B follow-up link): weight = 2 (effort = 2 units)
    """
    items = []
    for o in opps:
        # Exclude blocked guardrails from autonomous optimization
        if getattr(o, "guardrail_status", "PASSED") == "BLOCKED":
            continue
            
        opp_type = getattr(o, "opportunity_type", "failed_payment")
        if opp_type in ["partial_payment", "overdue_payment"]:
            weight = 2
        else:
            weight = 1

        ev = float(getattr(o, "expected_value", 0.0))
        cust_name = o.customer.name if getattr(o, "customer", None) else "Customer"

        items.append(OptimizationItem(
            id=o.id,
            title=o.title,
            opportunity_type=opp_type,
            customer_name=cust_name,
            recoverable_amount=float(o.recoverable_amount),
            recovery_probability=float(o.recovery_probability),
            expected_value=ev,
            weight=weight,
            raw_cost=float(getattr(o, "action_cost", 5.0)),
            recommended_action=o.recommended_action,
            guardrail_status=o.guardrail_status
        ))
    return items

def solve_01_knapsack_dp(items: List[OptimizationItem], capacity: int) -> StrategyResult:
    """
    Solves the 0/1 Knapsack Problem using Dynamic Programming:
    Maximize Sum(EV_i) subject to Sum(Weight_i) <= Capacity.
    Time Complexity: O(M * W), Space Complexity: O(M * W).
    Exact optimal guarantee.
    """
    n = len(items)
    if n == 0 or capacity <= 0:
        return StrategyResult("0/1 Dynamic Programming (Optimal)", [], 0.0, 0.0, 0, capacity, 0, 0.0)

    # DP Table: dp[i][w] stores maximum EV using subset of first i items with weight limit w
    # Using integer scaling for EV in cents to ensure precise DP state transitions
    scale = 100
    dp = [[0 for _ in range(capacity + 1)] for _ in range(n + 1)]

    for i in range(1, n + 1):
        item = items[i - 1]
        ev_scaled = int(round(item.expected_value * scale))
        w = item.weight
        for cap in range(capacity + 1):
            if w <= cap:
                dp[i][cap] = max(dp[i - 1][cap], dp[i - 1][cap - w] + ev_scaled)
            else:
                dp[i][cap] = dp[i - 1][cap]

    # Reconstruct optimal subset
    selected: List[OptimizationItem] = []
    rem_cap = capacity
    for i in range(n, 0, -1):
        if dp[i][rem_cap] != dp[i - 1][rem_cap]:
            item = items[i - 1]
            selected.append(item)
            rem_cap -= item.weight

    selected.reverse()

    total_ev = round(sum(it.expected_value for it in selected), 2)
    total_rec = round(sum(it.recoverable_amount for it in selected), 2)
    total_w = sum(it.weight for it in selected)
    eff = round(total_ev / total_w, 2) if total_w > 0 else 0.0

    selected_dicts = [it._asdict() for it in selected]

    return StrategyResult(
        strategy_name="0/1 Dynamic Programming (Optimal)",
        selected_items=selected_dicts,
        total_expected_value=total_ev,
        total_recoverable_amount=total_rec,
        total_weight_used=total_w,
        capacity_limit=capacity,
        item_count=len(selected),
        efficiency_ratio=eff
    )

def solve_greedy_by_ratio(items: List[OptimizationItem], capacity: int) -> StrategyResult:
    """
    Heuristic Greedy Strategy:
    Sorts opportunities by density ratio r_i = EV_i / Weight_i.
    Greedily selects highest density items until capacity is exhausted.
    """
    if not items or capacity <= 0:
        return StrategyResult("Greedy Density Ratio (EV/Cost)", [], 0.0, 0.0, 0, capacity, 0, 0.0)

    # Sort descending by ratio: EV / weight
    sorted_items = sorted(items, key=lambda it: (it.expected_value / it.weight), reverse=True)

    selected: List[OptimizationItem] = []
    total_w = 0

    for it in sorted_items:
        if total_w + it.weight <= capacity:
            selected.append(it)
            total_w += it.weight

    total_ev = round(sum(it.expected_value for it in selected), 2)
    total_rec = round(sum(it.recoverable_amount for it in selected), 2)
    eff = round(total_ev / total_w, 2) if total_w > 0 else 0.0

    selected_dicts = [it._asdict() for it in selected]

    return StrategyResult(
        strategy_name="Greedy Density Ratio (EV/Cost)",
        selected_items=selected_dicts,
        total_expected_value=total_ev,
        total_recoverable_amount=total_rec,
        total_weight_used=total_w,
        capacity_limit=capacity,
        item_count=len(selected),
        efficiency_ratio=eff
    )

def solve_naive_fifo(items: List[OptimizationItem], capacity: int) -> StrategyResult:
    """
    Naive Baseline Strategy:
    Takes opportunities in chronological / FIFO order until capacity is exhausted.
    """
    if not items or capacity <= 0:
        return StrategyResult("Naive Baseline (FIFO)", [], 0.0, 0.0, 0, capacity, 0, 0.0)

    selected: List[OptimizationItem] = []
    total_w = 0

    for it in items:
        if total_w + it.weight <= capacity:
            selected.append(it)
            total_w += it.weight

    total_ev = round(sum(it.expected_value for it in selected), 2)
    total_rec = round(sum(it.recoverable_amount for it in selected), 2)
    eff = round(total_ev / total_w, 2) if total_w > 0 else 0.0

    selected_dicts = [it._asdict() for it in selected]

    return StrategyResult(
        strategy_name="Naive Baseline (FIFO)",
        selected_items=selected_dicts,
        total_expected_value=total_ev,
        total_recoverable_amount=total_rec,
        total_weight_used=total_w,
        capacity_limit=capacity,
        item_count=len(selected),
        efficiency_ratio=eff
    )

def run_constrained_optimization_comparison(
    opps: List[Any],
    capacity_budget: int = 10
) -> OptimizationComparison:
    """
    Runs all 3 strategies on the same opportunity set and computes exact mathematical lift.
    """
    items = prepare_items_from_opportunities(opps)

    dp_res = solve_01_knapsack_dp(items, capacity_budget)
    greedy_res = solve_greedy_by_ratio(items, capacity_budget)
    naive_res = solve_naive_fifo(items, capacity_budget)

    # Compute Lift over Naive
    if naive_res.total_expected_value > 0:
        lift_naive = round(((dp_res.total_expected_value - naive_res.total_expected_value) / naive_res.total_expected_value) * 100, 1)
    else:
        lift_naive = 100.0 if dp_res.total_expected_value > 0 else 0.0

    # Compute Lift over Greedy
    if greedy_res.total_expected_value > 0:
        lift_greedy = round(((dp_res.total_expected_value - greedy_res.total_expected_value) / greedy_res.total_expected_value) * 100, 1)
    else:
        lift_greedy = 0.0

    return OptimizationComparison(
        optimal_dp=dp_res,
        greedy_ratio=greedy_res,
        naive_fifo=naive_res,
        capacity_budget=capacity_budget,
        total_opportunities_evaluated=len(items),
        dp_lift_over_naive_percent=lift_naive,
        dp_lift_over_greedy_percent=lift_greedy
    )