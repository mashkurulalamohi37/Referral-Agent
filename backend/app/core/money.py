"""Money primitives (§2, ADR 0003).

Rules:
- Amounts are integer minor units (poisha for BDT). `float` is never accepted.
- Intermediate maths uses `Decimal` (or exact integer arithmetic) and rounds once,
  `ROUND_HALF_UP` to the minor unit, at the end of a calculation.
- `ROUND_HALF_UP` rounds halves away from zero: 2.5 -> 3, -2.5 -> -3.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation, localcontext
from typing import Self

# ISO-4217 minor-unit exponents for currencies the schema supports. Enabling a currency is
# a settings decision (Q13: BDT only in v1); being listed here only makes it representable.
CURRENCY_EXPONENTS: dict[str, int] = {
    "BDT": 2,
    "USD": 2,
    "EUR": 2,
    "GBP": 2,
    "INR": 2,
    "JPY": 0,
}

BPS_DENOMINATOR = 10_000
_DECIMAL_CONTEXT = Context(prec=38, rounding=ROUND_HALF_UP)
_ONE = Decimal(1)


class MoneyError(ValueError):
    pass


class CurrencyMismatchError(MoneyError):
    pass


def _check_int(value: object, name: str) -> int:
    # bool is a subclass of int; reject it along with float and Decimal.
    if type(value) is not int:
        msg = f"{name} must be int minor units, got {type(value).__name__}"
        raise MoneyError(msg)
    return value


def exponent(currency: str) -> int:
    try:
        return CURRENCY_EXPONENTS[currency]
    except KeyError:
        msg = f"unsupported currency {currency!r}"
        raise MoneyError(msg) from None


@dataclass(frozen=True, slots=True)
class Money:
    amount_minor: int
    currency: str

    def __post_init__(self) -> None:
        _check_int(self.amount_minor, "amount_minor")
        exponent(self.currency)

    @classmethod
    def zero(cls, currency: str) -> Self:
        return cls(0, currency)

    def _same(self, other: Money) -> None:
        if not isinstance(other, Money):
            msg = f"expected Money, got {type(other).__name__}"
            raise MoneyError(msg)
        if other.currency != self.currency:
            msg = f"{self.currency} vs {other.currency}"
            raise CurrencyMismatchError(msg)

    def __add__(self, other: Money) -> Money:
        self._same(other)
        return Money(self.amount_minor + other.amount_minor, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same(other)
        return Money(self.amount_minor - other.amount_minor, self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount_minor, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._same(other)
        return self.amount_minor < other.amount_minor

    def __le__(self, other: Money) -> bool:
        self._same(other)
        return self.amount_minor <= other.amount_minor

    def __gt__(self, other: Money) -> bool:
        self._same(other)
        return self.amount_minor > other.amount_minor

    def __ge__(self, other: Money) -> bool:
        self._same(other)
        return self.amount_minor >= other.amount_minor

    @property
    def is_zero(self) -> bool:
        return self.amount_minor == 0

    @property
    def is_negative(self) -> bool:
        return self.amount_minor < 0

    def min(self, other: Money) -> Money:
        return self if self <= other else other

    def to_major_str(self) -> str:
        """Exact decimal string in major units, e.g. 20000 BDT -> '200.00'."""
        exp = exponent(self.currency)
        value = Decimal(self.amount_minor).scaleb(-exp)
        return f"{value:.{exp}f}"

    @classmethod
    def from_major(cls, text: str, currency: str) -> Self:
        """Parse a major-unit decimal string ('200.50'). Rejects more decimals than the currency has."""
        exp = exponent(currency)
        try:
            value = Decimal(text.strip())
        except InvalidOperation:
            msg = f"invalid amount {text!r}"
            raise MoneyError(msg) from None
        if not value.is_finite():
            msg = f"invalid amount {text!r}"
            raise MoneyError(msg)
        minor = value.scaleb(exp)
        if minor != minor.to_integral_value():
            msg = f"{text!r} has more than {exp} decimal places for {currency}"
            raise MoneyError(msg)
        return cls(int(minor), currency)

    def __str__(self) -> str:
        return f"{self.to_major_str()} {self.currency}"


def round_minor(value: Decimal) -> int:
    """Round a Decimal amount of minor units to an int, ROUND_HALF_UP. The one rounding step."""
    if not isinstance(value, Decimal):
        msg = f"round_minor expects Decimal, got {type(value).__name__}"
        raise MoneyError(msg)
    with localcontext(_DECIMAL_CONTEXT):
        return int(value.quantize(_ONE, rounding=ROUND_HALF_UP))


def apply_bps(amount_minor: int, rate_bps: int) -> int:
    """amount × rate_bps / 10000, rounded once (PERCENTAGE commission, §9.3)."""
    _check_int(amount_minor, "amount_minor")
    _check_int(rate_bps, "rate_bps")
    return mul_div_round(amount_minor, rate_bps, BPS_DENOMINATOR)


def mul_div_round(amount: int, numerator: int, denominator: int) -> int:
    """round_half_up(amount × numerator / denominator) using exact integer arithmetic."""
    _check_int(amount, "amount")
    _check_int(numerator, "numerator")
    _check_int(denominator, "denominator")
    if denominator <= 0:
        msg = "denominator must be positive"
        raise MoneyError(msg)
    product = amount * numerator
    sign = -1 if product < 0 else 1
    # half-up on the magnitude == half away from zero overall
    return sign * ((2 * abs(product) + denominator) // (2 * denominator))


def allocate(total: int, weights: Sequence[int]) -> list[int]:
    """Split `total` by integer `weights` so the parts sum exactly to `total`.

    Largest-remainder method: each part gets floor(total × w / Σw); leftover units go to the
    parts with the largest remainders, ties broken by position (earlier first). Callers rely on
    that tie rule (ADR 0008: `available` is listed before `credit_only`).
    Negative totals are allocated by magnitude and negated, so allocate(-t, w) == -allocate(t, w).
    """
    _check_int(total, "total")
    if not weights:
        msg = "weights must not be empty"
        raise MoneyError(msg)
    for w in weights:
        _check_int(w, "weight")
        if w < 0:
            msg = "weights must be non-negative"
            raise MoneyError(msg)
    weight_sum = sum(weights)
    if weight_sum == 0:
        msg = "weights must not all be zero"
        raise MoneyError(msg)
    if total < 0:
        return [-part for part in allocate(-total, weights)]

    parts = [total * w // weight_sum for w in weights]
    remainders = [total * w % weight_sum for w in weights]
    leftover = total - sum(parts)
    order = sorted(range(len(weights)), key=lambda i: (-remainders[i], i))
    for i in order[:leftover]:
        parts[i] += 1
    return parts
