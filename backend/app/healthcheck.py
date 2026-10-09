"""Container health checks (the runtime image has no curl).

    python -m app.healthcheck api      # GET /v1/health on localhost:8000
    python -m app.healthcheck beat     # heartbeat task ran within the last 3 minutes
"""

from __future__ import annotations

import sys
import urllib.request
from datetime import datetime, timedelta

from redis import Redis

from app.core import clock
from app.core.config import get_settings

_MAX_HEARTBEAT_AGE = timedelta(minutes=3)


def check_api() -> bool:
    with urllib.request.urlopen("http://127.0.0.1:8000/v1/health", timeout=3) as resp:  # noqa: S310
        return bool(resp.status == 200)


def check_beat() -> bool:
    from app.worker.tasks import HEARTBEAT_KEY  # noqa: PLC0415 - avoid importing Celery for api checks

    client = Redis.from_url(str(get_settings().redis_url), decode_responses=True)
    try:
        value = client.get(HEARTBEAT_KEY)
    finally:
        client.close()
    if not isinstance(value, str):
        return False
    return clock.now() - datetime.fromisoformat(value) < _MAX_HEARTBEAT_AGE


def main(argv: list[str]) -> int:
    checks = {"api": check_api, "beat": check_beat}
    if len(argv) != 2 or argv[1] not in checks:
        print(f"usage: python -m app.healthcheck {{{'|'.join(checks)}}}", file=sys.stderr)  # noqa: T201
        return 2
    try:
        return 0 if checks[argv[1]]() else 1
    except Exception as exc:  # any failure means unhealthy
        print(f"unhealthy: {type(exc).__name__}", file=sys.stderr)  # noqa: T201
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
