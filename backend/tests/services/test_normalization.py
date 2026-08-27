from uuid import UUID

from app.domain.enums import Condition, ProductCategory
from app.domain.normalization import NormalizationCandidate
from app.services.normalization import normalize_listing

RTX_3060_12 = NormalizationCandidate(
    product_id=UUID("00000000-0000-0000-0000-000000000012"),
    category=ProductCategory.GPU,
    alias="rtx 3060",
    required_tokens=frozenset({"12gb"}),
    excluded_tokens=frozenset({"ti", "8gb"}),
)
RTX_3060_TI = NormalizationCandidate(
    product_id=UUID("00000000-0000-0000-0000-000000000013"),
    category=ProductCategory.GPU,
    alias="rtx 3060 ti",
    required_tokens=frozenset({"ti"}),
    excluded_tokens=frozenset(),
)


def test_exact_gpu_variant_is_resolved() -> None:
    result = normalize_listing(
        "MSI GeForce RTX 3060 12 GB Gaming X",
        "voll funktionsfähig und getestet",
        [RTX_3060_12, RTX_3060_TI],
    )

    assert result.product_id == RTX_3060_12.product_id
    assert result.condition is Condition.USED
    assert result.confidence_bps == 10000
    assert result.review_required is False


def test_defective_and_empty_box_language_blocks_resolution() -> None:
    result = normalize_listing(
        "RTX 3060 12GB OVP",
        "Nur Verpackung, Karte defekt und nicht enthalten",
        [RTX_3060_12],
    )

    assert result.condition is Condition.DEFECTIVE
    assert set(result.flags) == {"DEFECTIVE", "EMPTY_BOX_RISK"}
    assert result.review_required is True


def test_missing_variant_stays_in_review() -> None:
    result = normalize_listing("RTX 3060 Grafikkarte", "gebraucht", [RTX_3060_12])

    assert result.product_id is None
    assert "UNCLEAR_VARIANT" in result.flags
    assert result.review_required is True
