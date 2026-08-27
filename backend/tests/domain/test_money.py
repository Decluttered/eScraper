import pytest

from app.domain.money import Money, apply_basis_points


def test_money_addition_requires_same_currency() -> None:
    assert Money(1250) + Money(275) == Money(1525)


def test_basis_points_round_half_up() -> None:
    assert apply_basis_points(25690, 500) == 1285


def test_money_rejects_non_integer_cents() -> None:
    with pytest.raises(TypeError, match="integer cents"):
        Money(12.5)  # type: ignore[arg-type]
