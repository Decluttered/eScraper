from dataclasses import dataclass

from app.domain.enums import ConfidenceLevel, Recommendation


@dataclass(frozen=True, slots=True)
class EvaluationPolicy:
    minimum_expected_profit_cents: int
    minimum_roi_bps: int
    minimum_downside_profit_cents: int
    risk_saturation_bps: int


@dataclass(frozen=True, slots=True)
class GateMetrics:
    expected_profit_cents: int
    downside_profit_cents: int
    roi_bps: int

    def passes(self, policy: EvaluationPolicy) -> bool:
        return (
            self.expected_profit_cents >= policy.minimum_expected_profit_cents
            and self.downside_profit_cents >= policy.minimum_downside_profit_cents
            and self.roi_bps >= policy.minimum_roi_bps
        )


@dataclass(frozen=True, slots=True)
class ScoreInputs:
    expected_profit_cents: int
    roi_bps: int
    liquidity_bps: int
    confidence: ConfidenceLevel
    risk_reserve_cents: int
    expected_sale_receipts_cents: int


@dataclass(frozen=True, slots=True)
class RecommendationInputs:
    asking_landed_cents: int
    maximum_purchase_price_cents: int
    confidence: ConfidenceLevel
    stale: bool
    ambiguous: bool
    blocking_risk: bool
    viable_purchase_price: bool


def _round_positive_ratio(numerator: int, denominator: int) -> int:
    if denominator <= 0:
        return 0
    return (2 * numerator + denominator) // (2 * denominator)


def _target_score(value: int, target: int) -> int:
    if target <= 0:
        return 100 if value >= 0 else 0
    if value <= 0:
        return 0
    if value <= target:
        return _round_positive_ratio(value * 50, target)
    return min(100, 50 + _round_positive_ratio((value - target) * 50, target))


def calculate_score(inputs: ScoreInputs, policy: EvaluationPolicy) -> int:
    confidence_score = {
        ConfidenceLevel.LOW: 25,
        ConfidenceLevel.MEDIUM: 65,
        ConfidenceLevel.HIGH: 100,
    }[inputs.confidence]
    saturation = max(1, policy.risk_saturation_bps)
    risk_ratio_bps = (
        _round_positive_ratio(
            inputs.risk_reserve_cents * 10000,
            inputs.expected_sale_receipts_cents,
        )
        if inputs.expected_sale_receipts_cents > 0
        else saturation
    )
    inverse_risk = max(0, 100 - _round_positive_ratio(risk_ratio_bps * 100, saturation))
    liquidity_score = max(0, min(100, _round_positive_ratio(inputs.liquidity_bps, 100)))
    weighted_numerator = (
        35 * _target_score(inputs.expected_profit_cents, policy.minimum_expected_profit_cents)
        + 20 * _target_score(inputs.roi_bps, policy.minimum_roi_bps)
        + 15 * liquidity_score
        + 15 * confidence_score
        + 15 * inverse_risk
    )
    return _round_positive_ratio(weighted_numerator, 100)


def recommend(inputs: RecommendationInputs) -> Recommendation:
    if inputs.blocking_risk or not inputs.viable_purchase_price:
        return Recommendation.REJECT
    if inputs.ambiguous or inputs.stale or inputs.confidence is ConfidenceLevel.LOW:
        return Recommendation.WATCH
    if inputs.asking_landed_cents <= inputs.maximum_purchase_price_cents:
        return Recommendation.BUY
    return Recommendation.NEGOTIATE
