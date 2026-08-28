import pytest

from app.domain.money import Money, apply_basis_points


def test_money_addition_requires_same_currency() -> None:
    assert Money(1250) + Money(275) == Money(1525)


def test_basis_points_round_half_up() -> None:
    assert apply_basis_points(25690, 500) == 1285


def test_money_rejects_non_integer_cents() -> None:
    with pytest.raises(TypeError, match="integer cents"):
        Money(12.5)  # type: ignore[arg-type]


def test_apply_basis_points_accepts_zero_rate() -> None:
    assert apply_basis_points(12345, 0) == 0


def test_apply_basis_points_accepts_full_hundred_percent() -> None:
    assert apply_basis_points(12345, 10_000) == 12345


def test_apply_basis_points_rejects_negative_rate() -> None:
    with pytest.raises(ValueError, match="basis points"):
        apply_basis_points(12345, -1)


def test_apply_basis_points_rejects_rate_above_one_hundred_percent() -> None:
    with pytest.raises(ValueError, match="basis points"):
        apply_basis_points(12345, 10_001)


def test_apply_basis_points_rejects_bool() -> None:
    with pytest.raises(TypeError, match="integer"):
        apply_basis_points(12345, True)  # type: ignore[arg-type]


def test_money_rejects_negative_cents() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        Money(-1)


def test_money_rejects_bool_cents() -> None:
    with pytest.raises(TypeError, match="integer"):
        Money(True)  # type: ignore[arg-type]
