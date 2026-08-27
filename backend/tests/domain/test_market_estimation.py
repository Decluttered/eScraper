from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.enums import ComparableStatus, ConfidenceLevel, Condition
from app.domain.market import ComparableEvidence, MarketEstimationConfig
from app.services.market_estimation import estimate_market

NOW = datetime(2026, 8, 27, tzinfo=UTC)
PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000012")


def sold(index: int, price_cents: int, age_days: int = 5) -> ComparableEvidence:
    return ComparableEvidence(
        id=f"sold-{index}",
        product_id=PRODUCT_ID,
        status=ComparableStatus.SOLD,
        condition=Condition.USED,
        item_price_cents=price_cents,
        shipping_cents=690,
        occurred_at=NOW - timedelta(days=age_days),
        variant_match_confidence_bps=10000,
        observation_count=1,
        sold_through_bps=7000,
    )


def test_active_asks_do_not_change_realized_percentiles() -> None:
    evidence = [sold(index, 24000 + index * 100) for index in range(8)]
    evidence.append(
        ComparableEvidence(
            id="active-high",
            product_id=PRODUCT_ID,
            status=ComparableStatus.ACTIVE,
            condition=Condition.USED,
            item_price_cents=99900,
            shipping_cents=0,
            occurred_at=NOW,
            variant_match_confidence_bps=10000,
            observation_count=1,
            sold_through_bps=None,
        )
    )

    result = estimate_market(evidence, NOW, MarketEstimationConfig())

    assert result.expected_item_price_cents < 25000
    assert result.confidence is ConfidenceLevel.MEDIUM
    assert "active-high" not in result.comparable_ids


def test_fewer_than_eight_exact_sales_is_low_confidence() -> None:
    result = estimate_market(
        [sold(index, 24000 + index * 100) for index in range(7)],
        NOW,
        MarketEstimationConfig(),
    )

    assert result.confidence is ConfidenceLevel.LOW
