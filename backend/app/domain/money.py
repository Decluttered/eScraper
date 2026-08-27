from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import Currency


def _round_decimal(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def apply_basis_points(cents: int, basis_points: int) -> int:
    if not isinstance(cents, int) or not isinstance(basis_points, int):
        raise TypeError("amount and rate must use integers")
    return _round_decimal(Decimal(cents) * Decimal(basis_points) / Decimal(10_000))


@dataclass(frozen=True, slots=True)
class Money:
    cents: int
    currency: Currency = Currency.EUR

    def __post_init__(self) -> None:
        if not isinstance(self.cents, int):
            raise TypeError("money must use integer cents")

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents - other.cents, self.currency)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency is not other.currency:
            raise ValueError("currency mismatch")
