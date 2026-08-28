from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import TaxProfileType
from app.domain.money import apply_basis_points


@dataclass(frozen=True, slots=True)
class FeeProfile:
    platform_fee_bps: int
    fixed_fee_cents: int
    fee_vat_bps: int
    fee_vat_recoverable: bool


@dataclass(frozen=True, slots=True)
class RiskInputs:
    return_probability_bps: int
    expected_return_cost_cents: int
    defect_probability_bps: int
    expected_defect_loss_cents: int
    fraud_probability_bps: int
    expected_fraud_loss_cents: int


@dataclass(frozen=True, slots=True)
class FinancialInputs:
    resale_item_price_cents: int
    buyer_shipping_cents: int
    purchase_price_cents: int
    outbound_shipping_cents: int
    packaging_cents: int
    refurbishment_cents: int
    travel_cents: int
    labor_cents: int
    advertising_cents: int
    fee: FeeProfile
    risk: RiskInputs
    tax_profile: TaxProfileType
    recoverable_input_vat_cents: int
    margin_scheme_supplier_eligible: bool

    @classmethod
    def minimum(
        cls,
        resale_item_price_cents: int,
        purchase_price_cents: int,
        tax_profile: TaxProfileType,
    ) -> "FinancialInputs":
        return cls(
            resale_item_price_cents=resale_item_price_cents,
            buyer_shipping_cents=0,
            purchase_price_cents=purchase_price_cents,
            outbound_shipping_cents=0,
            packaging_cents=0,
            refurbishment_cents=0,
            travel_cents=0,
            labor_cents=0,
            advertising_cents=0,
            fee=FeeProfile(0, 0, 0, True),
            risk=RiskInputs(0, 0, 0, 0, 0, 0),
            tax_profile=tax_profile,
            recoverable_input_vat_cents=0,
            margin_scheme_supplier_eligible=False,
        )


@dataclass(frozen=True, slots=True)
class FinancialResult:
    sale_receipts_cents: int
    platform_fee_cents: int
    fee_vat_cents: int
    risk_reserve_cents: int
    estimated_tax_cents: int
    contribution_profit_cents: int
    roi_bps: int


def _risk_reserve(risk: RiskInputs) -> int:
    return (
        apply_basis_points(risk.expected_return_cost_cents, risk.return_probability_bps)
        + apply_basis_points(risk.expected_defect_loss_cents, risk.defect_probability_bps)
        + apply_basis_points(risk.expected_fraud_loss_cents, risk.fraud_probability_bps)
    )


def _rounded_ratio(numerator: int, denominator: int) -> int:
    if denominator == 0:
        return 0
    value = Decimal(numerator) / Decimal(denominator)
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _estimated_tax(inputs: FinancialInputs, sale_receipts_cents: int) -> int:
    if inputs.tax_profile in {TaxProfileType.PRIVATE, TaxProfileType.SMALL_BUSINESS}:
        return 0
    if inputs.tax_profile is TaxProfileType.STANDARD_VAT:
        output_vat = _rounded_ratio(sale_receipts_cents * 19, 119)
        return max(0, output_vat - inputs.recoverable_input_vat_cents)
    if not inputs.margin_scheme_supplier_eligible:
        raise ValueError("margin scheme requires an eligible supplier record")
    gross_margin = max(0, sale_receipts_cents - inputs.purchase_price_cents)
    return _rounded_ratio(gross_margin * 19, 119)


def calculate_financials(inputs: FinancialInputs) -> FinancialResult:
    sale_receipts = inputs.resale_item_price_cents + inputs.buyer_shipping_cents
    platform_fee = apply_basis_points(sale_receipts, inputs.fee.platform_fee_bps)
    platform_fee += inputs.fee.fixed_fee_cents
    fee_vat = 0 if inputs.fee.fee_vat_recoverable else apply_basis_points(
        platform_fee, inputs.fee.fee_vat_bps
    )
    reserve = _risk_reserve(inputs.risk)
    tax = _estimated_tax(inputs, sale_receipts)
    direct_costs = (
        inputs.purchase_price_cents
        + inputs.outbound_shipping_cents
        + inputs.packaging_cents
        + inputs.refurbishment_cents
        + inputs.travel_cents
        + inputs.labor_cents
        + inputs.advertising_cents
    )
    profit = sale_receipts - direct_costs - platform_fee - fee_vat - reserve - tax
    roi = _rounded_ratio(profit * 10000, inputs.purchase_price_cents)
    return FinancialResult(
        sale_receipts_cents=sale_receipts,
        platform_fee_cents=platform_fee,
        fee_vat_cents=fee_vat,
        risk_reserve_cents=reserve,
        estimated_tax_cents=tax,
        contribution_profit_cents=profit,
        roi_bps=roi,
    )
