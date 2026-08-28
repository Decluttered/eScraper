import pytest

from app.domain.enums import TaxProfileType
from app.domain.finance import FeeProfile, FinancialInputs, RiskInputs, calculate_financials


def test_small_business_contribution_includes_fee_vat_and_reserves() -> None:
    result = calculate_financials(
        FinancialInputs(
            resale_item_price_cents=25000,
            buyer_shipping_cents=690,
            purchase_price_cents=18000,
            outbound_shipping_cents=690,
            packaging_cents=200,
            refurbishment_cents=0,
            travel_cents=0,
            labor_cents=1000,
            advertising_cents=0,
            fee=FeeProfile(500, 45, 1900, False),
            risk=RiskInputs(500, 1000, 300, 5000, 100, 10000),
            tax_profile=TaxProfileType.SMALL_BUSINESS,
            recoverable_input_vat_cents=0,
            margin_scheme_supplier_eligible=False,
        )
    )

    assert result.platform_fee_cents == 1330
    assert result.fee_vat_cents == 253
    assert result.risk_reserve_cents == 300
    assert result.estimated_tax_cents == 0
    assert result.contribution_profit_cents == 3917


def test_margin_scheme_requires_eligible_supplier_record() -> None:
    inputs = FinancialInputs.minimum(
        resale_item_price_cents=25000,
        purchase_price_cents=18000,
        tax_profile=TaxProfileType.MARGIN_SCHEME,
    )

    with pytest.raises(ValueError, match="eligible supplier"):
        calculate_financials(inputs)
