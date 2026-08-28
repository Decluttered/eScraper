from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PartOutComponent:
    component_id: str
    downside_sale_receipts_cents: int
    platform_fee_cents: int
    shipping_cents: int
    packaging_cents: int
    incremental_labor_cents: int
    risk_reserve_cents: int


@dataclass(frozen=True, slots=True)
class PartOutResult:
    complete_pc_profit_cents: int
    part_out_profit_cents: int
    selected_scenario: str


def evaluate_part_out(
    complete_pc_downside_profit_cents: int,
    components: list[PartOutComponent],
    residual_loss_cents: int,
) -> PartOutResult:
    identities = [component.component_id for component in components]
    if len(identities) != len(set(identities)):
        raise ValueError("duplicate component in part-out scenario")
    part_out_profit = -residual_loss_cents
    for component in components:
        part_out_profit += (
            component.downside_sale_receipts_cents
            - component.platform_fee_cents
            - component.shipping_cents
            - component.packaging_cents
            - component.incremental_labor_cents
            - component.risk_reserve_cents
        )
    selected = (
        "PART_OUT"
        if part_out_profit > complete_pc_downside_profit_cents
        else "COMPLETE_PC"
    )
    return PartOutResult(
        complete_pc_profit_cents=complete_pc_downside_profit_cents,
        part_out_profit_cents=part_out_profit,
        selected_scenario=selected,
    )
