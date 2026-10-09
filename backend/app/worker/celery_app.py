"""Celery application (workers and Beat). Start with:

    celery -A app.worker.celery_app worker --pool=prefork
    celery -A app.worker.celery_app beat
"""

from __future__ import annotations

from typing import Any

from celery import Celery
from celery.signals import setup_logging, worker_process_init, worker_process_shutdown

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.worker import runtime

settings = get_settings()

celery_app = Celery("referral", broker=str(settings.redis_url), include=["app.worker.tasks"])
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_backend=None,
    task_ignore_result=True,
    timezone="UTC",
    enable_utc=True,
    # At-least-once delivery: tasks are idempotent (§2), so redelivery after a crash is safe.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_default_queue="default",
    beat_schedule={
        "heartbeat": {"task": "system.heartbeat", "schedule": 60.0},
    },
)


@setup_logging.connect
def _setup_logging(**_: Any) -> None:
    configure_logging(settings.log_level)


@worker_process_init.connect
def _init_worker_process(**_: Any) -> None:
    runtime.init_process()


@worker_process_shutdown.connect
def _shutdown_worker_process(**_: Any) -> None:
    runtime.shutdown_process()
