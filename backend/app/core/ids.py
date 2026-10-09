"""RFC 9562 UUIDv7 generation (ADR 0003).

Layout: 48-bit Unix timestamp in ms | version 7 | 12 bits rand_a | variant 0b10 | 62 bits rand_b.
The 74 random bits are treated as one counter that is incremented for calls within the same
millisecond (or when the clock steps backwards), so IDs from one process are strictly increasing.
"""

from __future__ import annotations

import secrets
import threading
import time
import uuid
from datetime import UTC, datetime

_RAND_BITS = 74
_RAND_MASK = (1 << _RAND_BITS) - 1
_RAND_B_BITS = 62
_MAX_MS = (1 << 48) - 1

_lock = threading.Lock()
_last_ms = -1
_last_rand = 0


def _fresh_random() -> int:
    # Leave headroom so the in-millisecond counter practically never overflows.
    return secrets.randbits(_RAND_BITS) >> 1


def uuid7() -> uuid.UUID:
    global _last_ms, _last_rand  # noqa: PLW0603 - process-wide monotonic state
    with _lock:
        ms = time.time_ns() // 1_000_000
        if ms > _last_ms:
            rand = _fresh_random()
        else:
            ms = _last_ms
            rand = _last_rand + 1
            if rand > _RAND_MASK:
                ms += 1
                rand = _fresh_random()
        if ms > _MAX_MS:
            msg = "UUIDv7 timestamp overflow"
            raise OverflowError(msg)
        _last_ms, _last_rand = ms, rand

    rand_a = rand >> _RAND_B_BITS
    rand_b = rand & ((1 << _RAND_B_BITS) - 1)
    value = (ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


def uuid7_timestamp(value: uuid.UUID) -> datetime:
    """Creation time encoded in a UUIDv7 (millisecond precision, UTC)."""
    if value.version != 7:  # noqa: PLR2004
        msg = "not a UUIDv7"
        raise ValueError(msg)
    return datetime.fromtimestamp((value.int >> 80) / 1000, tz=UTC)
