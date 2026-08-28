import pytest

from app.domain.part_out import PartOutComponent, evaluate_part_out


def test_duplicate_component_identity_is_rejected() -> None:
    component = PartOutComponent("gpu-1", 25000, 1330, 690, 200, 500, 300)

    with pytest.raises(ValueError, match="duplicate component"):
        evaluate_part_out(4500, [component, component], 0)


def test_part_out_subtracts_every_per_item_cost() -> None:
    result = evaluate_part_out(
        complete_pc_downside_profit_cents=4500,
        components=[
            PartOutComponent("gpu-1", 25000, 1330, 690, 200, 500, 300),
            PartOutComponent("cpu-1", 9500, 520, 290, 100, 250, 100),
        ],
        residual_loss_cents=2000,
    )

    assert result.part_out_profit_cents == 28220
    assert result.selected_scenario == "PART_OUT"
