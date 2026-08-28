from collections.abc import Callable

from app.domain.scoring import EvaluationPolicy, GateMetrics


def solve_max_purchase_price(
    upper_bound_cents: int,
    policy: EvaluationPolicy,
    evaluate: Callable[[int], GateMetrics],
) -> int:
    low = 0
    high = max(0, upper_bound_cents)
    best = -1
    while low <= high:
        candidate = (low + high) // 2
        if evaluate(candidate).passes(policy):
            best = candidate
            low = candidate + 1
        else:
            high = candidate - 1
    return best
