from app.domain.scoring import EvaluationPolicy, GateMetrics
from app.services.max_purchase import solve_max_purchase_price


POLICY = EvaluationPolicy(1500, 1500, 0, 2000)


def metrics(purchase_price_cents: int) -> GateMetrics:
    expected_profit = 20000 - purchase_price_cents
    downside_profit = 18000 - purchase_price_cents
    roi = (
        (2 * expected_profit * 10000 + purchase_price_cents) // (2 * purchase_price_cents)
        if purchase_price_cents
        else 10000
    )
    return GateMetrics(expected_profit, downside_profit, roi)


def test_solver_returns_highest_price_that_passes_all_gates() -> None:
    maximum = solve_max_purchase_price(25000, POLICY, metrics)

    assert metrics(maximum).passes(POLICY) is True
    assert metrics(maximum + 1).passes(POLICY) is False
