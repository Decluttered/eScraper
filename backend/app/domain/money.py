from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.domain.enums import Currency

MAX_BASIS_POINTS = 10_000


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _round_decimal(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def apply_basis_points(cents: int, basis_points: int) -> int:
    if not _is_int(cents) or not _is_int(basis_points):
        raise TypeError("amount and rate must use integers")
    if not 0 <= basis_points <= MAX_BASIS_POINTS:
        raise ValueError(
            "basis points must be between 0 and 10000 (0% to 100%) inclusive"
        )
    return _round_decimal(Decimal(cents) * Decimal(basis_points) / Decimal(10_000))


@dataclass(frozen=True, slots=True)
class Money:
    cents: int
    currency: Currency = Currency.EUR

    def __post_init__(self) -> None:
        if not _is_int(self.cents):
            raise TypeError("money must use integer cents")
        if self.cents < 0:
            raise ValueError("money cents must be non-negative")

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents + other.cents, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.cents - other.cents, self.currency)

    def _require_same_currency(self, other: "Money") -> None:
        if self.currency is not other.currency:
            raise ValueError("currency mismatch")
