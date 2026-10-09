from __future__ import annotations

from decimal import Decimal, localcontext

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.money import (
    CurrencyMismatchError,
    Money,
    MoneyError,
    allocate,
    apply_bps,
    mul_div_round,
    round_minor,
)

amounts = st.integers(min_value=-(10**15), max_value=10**15)
non_negative = st.integers(min_value=0, max_value=10**15)


class TestMoney:
    def test_rejects_float_bool_and_decimal(self) -> None:
        with pytest.raises(MoneyError):
            Money(10.0, "BDT")  # type: ignore[arg-type]
        with pytest.raises(MoneyError):
            Money(True, "BDT")
        with pytest.raises(MoneyError):
            Money(Decimal(10), "BDT")  # type: ignore[arg-type]

    def test_rejects_unknown_currency(self) -> None:
        with pytest.raises(MoneyError, match="unsupported currency"):
            Money(1, "XYZ")

    def test_arithmetic_and_comparison(self) -> None:
        a, b = Money(20000, "BDT"), Money(5000, "BDT")
        assert a + b == Money(25000, "BDT")
        assert a - b == Money(15000, "BDT")
        assert -b == Money(-5000, "BDT")
        assert b < a
        assert b <= a
        assert a > b
        assert a >= b
        assert a.min(b) == b
        assert b.min(a) == b
        assert Money.zero("BDT").is_zero
        assert (b - a).is_negative

    @pytest.mark.parametrize(
        "op",
        [
            lambda x, y: x + y,
            lambda x, y: x - y,
            lambda x, y: x < y,
            lambda x, y: x <= y,
            lambda x, y: x > y,
            lambda x, y: x >= y,
        ],
    )
    def test_currency_mismatch(self, op: object) -> None:
        with pytest.raises(CurrencyMismatchError):
            op(Money(1, "BDT"), Money(1, "USD"))  # type: ignore[operator]

    def test_operations_with_non_money(self) -> None:
        with pytest.raises(MoneyError, match="expected Money"):
            Money(1, "BDT") + 1  # type: ignore[operator]

    @pytest.mark.parametrize(
        ("minor", "currency", "text"),
        [
            (20000, "BDT", "200.00"),
            (5, "BDT", "0.05"),
            (-150, "BDT", "-1.50"),
            (1234, "JPY", "1234"),
        ],
    )
    def test_major_string_round_trip(self, minor: int, currency: str, text: str) -> None:
        money = Money(minor, currency)
        assert money.to_major_str() == text
        assert Money.from_major(text, currency) == money

    def test_str(self) -> None:
        assert str(Money(20000, "BDT")) == "200.00 BDT"

    @pytest.mark.parametrize("text", ["1.001", "abc", "NaN", "Infinity", ""])
    def test_from_major_rejects(self, text: str) -> None:
        with pytest.raises(MoneyError):
            Money.from_major(text, "BDT")

    def test_from_major_jpy_rejects_decimals(self) -> None:
        with pytest.raises(MoneyError):
            Money.from_major("1.5", "JPY")


class TestRounding:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("2.5", 3),
            ("2.4999999", 2),
            ("-2.5", -3),
            ("-2.4", -2),
            ("0.5", 1),
            ("0", 0),
            ("199999.5", 200000),
        ],
    )
    def test_round_half_up_away_from_zero(self, value: str, expected: int) -> None:
        assert round_minor(Decimal(value)) == expected

    def test_round_minor_rejects_float(self) -> None:
        with pytest.raises(MoneyError):
            round_minor(2.5)  # type: ignore[arg-type]

    def test_acceptance_commission(self) -> None:
        # ৳2,000 at 10% = ৳200 (spec §1).
        assert apply_bps(200_000, 1000) == 20_000

    @pytest.mark.parametrize(
        ("amount", "bps", "expected"),
        [
            (5, 1000, 1),  # 0.5 -> 1
            (4, 1000, 0),  # 0.4 -> 0
            (15, 1000, 2),  # 1.5 -> 2
            (1, 5000, 1),  # 0.5 -> 1
            (0, 1000, 0),
            (999_999, 1, 100),  # 99.9999 -> 100
            (-5, 1000, -1),
        ],
    )
    def test_apply_bps_edges(self, amount: int, bps: int, expected: int) -> None:
        assert apply_bps(amount, bps) == expected

    @given(amount=amounts, num=st.integers(-(10**6), 10**6), den=st.integers(1, 10**6))
    def test_mul_div_round_matches_decimal(self, amount: int, num: int, den: int) -> None:
        with localcontext() as ctx:
            ctx.prec = 60
            exact = Decimal(amount) * Decimal(num) / Decimal(den)
            assert mul_div_round(amount, num, den) == round_minor(exact)

    def test_mul_div_round_rejects_bad_denominator(self) -> None:
        with pytest.raises(MoneyError):
            mul_div_round(1, 1, 0)
        with pytest.raises(MoneyError):
            apply_bps(1.0, 100)  # type: ignore[arg-type]


class TestAllocate:
    def test_even_split(self) -> None:
        assert allocate(200, [50, 50]) == [100, 100]

    def test_adr_0008_example(self) -> None:
        # Reversal of 75 across a 50/50 split: tie goes to the first part (available).
        assert allocate(75, [100, 100]) == [38, 37]

    def test_largest_remainder_wins(self) -> None:
        assert allocate(10, [1, 1, 1]) == [4, 3, 3]
        assert allocate(100, [1, 2]) == [33, 67]

    def test_zero_weight_gets_nothing(self) -> None:
        assert allocate(7, [0, 3, 0, 4]) == [0, 3, 0, 4]
        assert allocate(5, [0, 1]) == [0, 5]

    def test_negative_total(self) -> None:
        assert allocate(-75, [100, 100]) == [-38, -37]

    @pytest.mark.parametrize("weights", [[], [0, 0], [-1, 2]])
    def test_invalid_weights(self, weights: list[int]) -> None:
        with pytest.raises(MoneyError):
            allocate(10, weights)

    def test_rejects_float_total(self) -> None:
        with pytest.raises(MoneyError):
            allocate(10.0, [1])  # type: ignore[arg-type]

    @given(
        total=amounts,
        weights=st.lists(st.integers(0, 10_000), min_size=1, max_size=8).filter(lambda w: sum(w) > 0),
    )
    def test_parts_sum_to_total_and_stay_within_one_unit(
        self, total: int, weights: list[int]
    ) -> None:
        parts = allocate(total, weights)
        assert sum(parts) == total
        weight_sum = sum(weights)
        for part, w in zip(parts, weights, strict=True):
            exact = Decimal(total) * w / weight_sum
            assert abs(Decimal(part) - exact) < 1
            if w == 0:
                assert part == 0

    @given(total=non_negative, weights=st.lists(st.integers(1, 100), min_size=1, max_size=5))
    def test_symmetric_for_negative(self, total: int, weights: list[int]) -> None:
        assert allocate(-total, weights) == [-p for p in allocate(total, weights)]
