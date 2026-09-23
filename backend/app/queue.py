"""Redis/RQ plumbing. The queue only carries job ids; the database is the source of truth."""

from datetime import timedelta

from redis import Redis
from rq import Queue

from app.config import get_settings
from app.logging import request_id_var

TASK_PATH = "worker.tasks.run_analysis_job"

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url)
    return _redis


def reset_redis() -> None:
    global _redis
    _redis = None


def get_queue() -> Queue:
    return Queue(get_settings().queue_name, connection=get_redis())


def enqueue_analysis(job_id: int, delay_seconds: float | None = None) -> None:
    """Put a job id on the queue, optionally after a delay (retry backoff).

    Delayed jobs need a worker started with the scheduler enabled (worker/run.py does).
    The current request id travels with the job so logs can be joined.
    """
    queue = get_queue()
    meta = {"request_id": request_id_var.get()}
    if delay_seconds and delay_seconds > 0:
        queue.enqueue_in(
            timedelta(seconds=delay_seconds), TASK_PATH, job_id, meta=meta, job_timeout=-1
        )
    else:
        queue.enqueue(TASK_PATH, job_id, meta=meta, job_timeout=-1)
