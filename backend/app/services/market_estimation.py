import math
import statistics
from datetime import datetime

from app.domain.enums import ComparableStatus, ConfidenceLevel
from app.domain.market import ComparableEvidence, MarketEstimate, MarketEstimationConfig


def _weighted_quantile(values: list[tuple[int, float]], quantile: float) -> int:
    ordered = sorted(values, key=lambda pair: pair[0])
    target = sum(weight for _, weight in ordered) * quantile
    cumulative = 0.0
    for value, weight in ordered:
        cumulative += weight
        if cumulative >= target:
            return value
    return ordered[-1][0]


def _remove_outliers(evidence: list[ComparableEvidence]) -> list[ComparableEvidence]:
    if len(evidence) < 7:
        return evidence
    prices = [row.item_price_cents for row in evidence]
    median = statistics.median(prices)
    deviations = [abs(price - median) for price in prices]
    mad = statistics.median(deviations)
    if mad == 0:
        return evidence
    return [row for row in evidence if abs(row.item_price_cents - median) <= 3 * mad]


def estimate_market(
    evidence: list[ComparableEvidence],
    now: datetime,
    config: MarketEstimationConfig,
) -> MarketEstimate:
    sold = _remove_outliers([row for row in evidence if row.status is ComparableStatus.SOLD])
    if not sold:
        return MarketEstimate(0, 0, 0, ConfidenceLevel.LOW, 0, (), None, True)

    weighted: list[tuple[int, float]] = []
    for row in sold:
        age_days = max(0.0, (now - row.occurred_at).total_seconds() / 86400)
        recency = math.pow(0.5, age_days / config.recency_half_life_days)
        variant = row.variant_match_confidence_bps / 10000
        weighted.append((row.item_price_cents, recency * variant * row.observation_count))

    exact_90 = sum(
        row.observation_count
        for row in sold
        if row.variant_match_confidence_bps == 10000
        and (now - row.occurred_at).days <= config.high_max_age_days
    )
    exact_180 = sum(
        row.observation_count
        for row in sold
        if row.variant_match_confidence_bps == 10000
        and (now - row.occurred_at).days <= config.medium_max_age_days
    )
    confidence = (
        ConfidenceLevel.HIGH
        if exact_90 >= config.high_min_sales
        else ConfidenceLevel.MEDIUM
        if exact_180 >= config.medium_min_sales
        else ConfidenceLevel.LOW
    )
    liquidity_values = [row.sold_through_bps for row in sold if row.sold_through_bps is not None]
    liquidity = round(sum(liquidity_values) / len(liquidity_values)) if liquidity_values else 0
    latest = max(row.occurred_at for row in sold)
    return MarketEstimate(
        downside_item_price_cents=_weighted_quantile(weighted, 0.25),
        expected_item_price_cents=_weighted_quantile(weighted, 0.50),
        optimistic_item_price_cents=_weighted_quantile(weighted, 0.75),
        confidence=confidence,
        liquidity_bps=max(0, min(10000, liquidity)),
        comparable_ids=tuple(row.id for row in sold),
        latest_sale_at=latest,
        stale=(now - latest).days > config.stale_after_days,
    )
