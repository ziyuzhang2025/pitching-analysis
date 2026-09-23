"""Start an RQ worker plus a background reaper thread (agent-written).

    python -m worker.run            # inside the backend/ directory

The worker runs with RQ's scheduler enabled, which delayed retries
(enqueue_analysis(job_id, delay)) need. Every REAPER_INTERVAL_SECONDS the reaper
re-queues jobs stuck in "running" (Exercise 6); until the exercise is done it logs a
warning and keeps going.
"""

import logging
import os
import socket
import threading
import time
from datetime import datetime, timezone

from rq import Worker

from app.config import get_settings
from app.db import session_factory
from app.logging import configure_logging, request_id_var
from app.queue import enqueue_analysis, get_queue, get_redis

REAPER_INTERVAL_SECONDS = int(os.environ.get("REAPER_INTERVAL_SECONDS", "60"))
log = logging.getLogger("pitchlab.worker")


def reap_once() -> list[int]:
    from app.jobs.reaper import requeue_stale_jobs

    settings = get_settings()
    with session_factory()() as db:
        ids = requeue_stale_jobs(db, datetime.now(timezone.utc), settings.job_timeout_seconds)
    for job_id in ids:
        enqueue_analysis(job_id)
    return ids


def reaper_loop(stop: threading.Event) -> None:
    while not stop.wait(REAPER_INTERVAL_SECONDS):
        try:
            ids = reap_once()
            if ids:
                log.warning("reaper re-queued stale jobs", extra={"job_id": ids})
        except NotImplementedError:
            log.warning("reaper not implemented yet (Exercise 6)")
        except Exception:
            log.exception("reaper failed")


class PitchLabWorker(Worker):
    """Carries the API request id (stored in job.meta) into the task's logs."""

    def perform_job(self, job, queue):  # type: ignore[no-untyped-def]
        token = request_id_var.set((job.meta or {}).get("request_id"))
        try:
            return super().perform_job(job, queue)
        finally:
            request_id_var.reset(token)


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    stop = threading.Event()
    threading.Thread(target=reaper_loop, args=(stop,), daemon=True).start()
    name = f"{socket.gethostname()}:{os.getpid()}:{int(time.time())}"
    worker = PitchLabWorker([get_queue()], connection=get_redis(), name=name)
    try:
        worker.work(with_scheduler=True)
    finally:
        stop.set()


if __name__ == "__main__":
    main()
