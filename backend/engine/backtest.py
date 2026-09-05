from typing import List, Dict, Any, NamedTuple
from .optimizer import prepare_items_from_opportunities, solve_01_knapsack_dp, solve_naive_fifo, OptimizationItem, StrategyResult

def solve_sort_by_ev_only(items: List[OptimizationItem], capacity: int) -> StrategyResult:
    if not items or capacity <= 0:
        return StrategyResult("Naive Sort by EV Only (Unconstrained)", [], 0.0, 0.0, 0, capacity, 0, 0.0)

    sorted_items = sorted(items, key=lambda it: it.expected_value, reverse=True)
    selected = []
    total_w = 0

    for it in sorted_items:
        if total_w + it.weight <= capacity:
            selected.append(it)
            total_w += it.weight

    total_ev = round(sum(it.expected_value for it in selected), 2)
    total_rec = round(sum(it.recoverable_amount for it in selected), 2)
    eff = round(total_ev / total_w, 2) if total_w > 0 else 0.0

    return StrategyResult(
        strategy_name="Naive Sort by EV Only (Unconstrained)",
        selected_items=[it._asdict() for it in selected],
        total_expected_value=total_ev,
        total_recoverable_amount=total_rec,
        total_weight_used=total_w,
        capacity_limit=capacity,
        item_count=len(selected),
        efficiency_ratio=eff
    )

def run_counterfactual_backtest(opps: List[Any], capacity_budget: int = 6) -> Dict[str, Any]:
    items = prepare_items_from_opportunities(opps)
    dp_res = solve_01_knapsack_dp(items, capacity=capacity_budget)
    ev_sort_res = solve_sort_by_ev_only(items, capacity=capacity_budget)
    fifo_res = solve_naive_fifo(items, capacity=capacity_budget)

    lift_vs_ev_sort = 0.0
    if ev_sort_res.total_expected_value > 0:
        lift_vs_ev_sort = round(
            ((dp_res.total_expected_value - ev_sort_res.total_expected_value) / ev_sort_res.total_expected_value) * 100, 
            1
        )

    lift_vs_fifo = 0.0
    if fifo_res.total_expected_value > 0:
        lift_vs_fifo = round(
            ((dp_res.total_expected_value - fifo_res.total_expected_value) / fifo_res.total_expected_value) * 100, 
            1
        )

    return {
        "capacity_budget": capacity_budget,
        "total_evaluated": len(items),
        "strategies": {
            "optimal_knapsack_dp": {
                "name": "0/1 Knapsack DP (RecoverIQ)",
                "total_ev": dp_res.total_expected_value,
                "item_count": dp_res.item_count,
                "effort_used": dp_res.total_weight_used,
                "efficiency": dp_res.efficiency_ratio,
                "selected_ids": [it["id"] for it in dp_res.selected_items]
            },
            "naive_sort_by_ev": {
                "name": "Naive Sort by EV Only",
                "total_ev": ev_sort_res.total_expected_value,
                "item_count": ev_sort_res.item_count,
                "effort_used": ev_sort_res.total_weight_used,
                "efficiency": ev_sort_res.efficiency_ratio,
                "selected_ids": [it["id"] for it in ev_sort_res.selected_items]
            },
            "naive_fifo": {
                "name": "Naive FIFO (Chronological)",
                "total_ev": fifo_res.total_expected_value,
                "item_count": fifo_res.item_count,
                "effort_used": fifo_res.total_weight_used,
                "efficiency": fifo_res.efficiency_ratio,
                "selected_ids": [it["id"] for it in fifo_res.selected_items]
            }
        },
        "counterfactual_lift": {
            "lift_over_sort_by_ev_percent": lift_vs_ev_sort,
            "lift_over_fifo_percent": lift_vs_fifo,
            "extra_revenue_unlocked": round(dp_res.total_expected_value - ev_sort_res.total_expected_value, 2)
        }
    }