from app.domain.enums import ConfidenceLevel, Recommendation
from app.domain.scoring import (
    EvaluationPolicy,
    RecommendationInputs,
    ScoreInputs,
    _target_score,
    calculate_score,
    recommend,
)


def test_low_confidence_caps_profitable_offer_at_watch() -> None:
    result = recommend(
        RecommendationInputs(
            asking_landed_cents=15000,
            maximum_purchase_price_cents=18000,
            confidence=ConfidenceLevel.LOW,
            stale=False,
            ambiguous=False,
            blocking_risk=False,
            viable_purchase_price=True,
        )
    )

    assert result is Recommendation.WATCH


def test_blocking_risk_rejects_offer_before_score() -> None:
    result = recommend(
        RecommendationInputs(15000, 18000, ConfidenceLevel.HIGH, False, False, True, True)
    )

    assert result is Recommendation.REJECT


def test_target_score_boundaries_are_integer_exact() -> None:
    assert _target_score(1000, 1000) == 50
    assert _target_score(2000, 1000) == 100
    assert _target_score(0, 1000) == 0


def test_missing_liquidity_and_saturated_risk_score_conservatively() -> None:
    policy = EvaluationPolicy(1000, 2000, 0, 2000)
    result = calculate_score(
        ScoreInputs(
            expected_profit_cents=1000,
            roi_bps=2000,
            liquidity_bps=0,
            confidence=ConfidenceLevel.LOW,
            risk_reserve_cents=2000,
            expected_sale_receipts_cents=10000,
        ),
        policy,
    )

    assert result == 31


def test_twice_target_reaches_full_profit_and_roi_components() -> None:
    policy = EvaluationPolicy(1000, 2000, 0, 2000)
    result = calculate_score(
        ScoreInputs(2000, 4000, 0, ConfidenceLevel.LOW, 0, 10000),
        policy,
    )

    assert result == 74
