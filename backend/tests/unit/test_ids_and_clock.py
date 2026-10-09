from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta, timezone
from unittest import mock

import pytest
from pydantic import BaseModel, ValidationError

from app.core import clock, ids


class TestUuid7:
    def test_version_and_variant(self) -> None:
        value = ids.uuid7()
        assert value.version == 7
        assert value.variant == uuid.RFC_4122

    def test_strictly_increasing_within_process(self) -> None:
        values = [ids.uuid7() for _ in range(10_000)]
        assert values == sorted(values)
        assert len(set(values)) == len(values)

    def test_timestamp_round_trip(self) -> None:
        before = datetime.now(UTC) - timedelta(milliseconds=5)
        value = ids.uuid7()
        after = datetime.now(UTC) + timedelta(milliseconds=5)
        assert before <= ids.uuid7_timestamp(value) <= after

    def test_monotonic_when_clock_goes_backwards(self) -> None:
        first = ids.uuid7()
        with mock.patch("app.core.ids.time.time_ns", return_value=0):
            second = ids.uuid7()
        assert second > first

    def test_counter_overflow_bumps_millisecond(self) -> None:
        first = ids.uuid7()
        ms = ids._last_ms
        with (
            mock.patch.object(ids, "_last_rand", ids._RAND_MASK),
            mock.patch("app.core.ids.time.time_ns", return_value=ms * 1_000_000),
        ):
            second = ids.uuid7()
        assert ids.uuid7_timestamp(second) > ids.uuid7_timestamp(first)

    def test_rejects_non_v7(self) -> None:
        with pytest.raises(ValueError, match="UUIDv7"):
            ids.uuid7_timestamp(uuid.uuid4())

    def test_timestamp_overflow(self) -> None:
        with (
            mock.patch("app.core.ids.time.time_ns", return_value=(1 << 48) * 1_000_000),
            pytest.raises(OverflowError),
        ):
            ids.uuid7()


class TestClock:
    def test_now_is_aware_utc(self) -> None:
        value = clock.now()
        assert value.tzinfo is UTC

    def test_frozen_and_advance(self) -> None:
        at = datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
        with clock.frozen(at) as frozen:
            assert clock.now() == at
            frozen.advance(timedelta(days=14))
            assert clock.now() == at + timedelta(days=14)
            frozen.set(datetime(2027, 1, 1, tzinfo=UTC))
            assert clock.now().year == 2027
        assert clock.now() != at

    def test_ensure_utc(self) -> None:
        dhaka = timezone(timedelta(hours=6))
        value = clock.ensure_utc(datetime(2026, 10, 8, 21, 0, tzinfo=dhaka))
        assert value == datetime(2026, 10, 8, 15, 0, tzinfo=UTC)
        assert value.tzinfo is UTC
        with pytest.raises(ValueError, match="timezone-aware"):
            clock.ensure_utc(datetime(2026, 10, 8))  # noqa: DTZ001

    def test_pydantic_type_rejects_naive(self) -> None:
        class Model(BaseModel):
            at: clock.UtcDatetime

        assert Model(at="2026-10-08T21:00:00+06:00").at.hour == 15  # type: ignore[arg-type]
        with pytest.raises(ValidationError):
            Model(at="2026-10-08T15:00:00")  # type: ignore[arg-type]
