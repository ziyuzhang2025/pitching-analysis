"""EXERCISE 6 (Ziyu): crash recovery.

If a worker process dies mid-job, the job stays "running" forever. The reaper finds
jobs running longer than a timeout and gives them another attempt (or fails them).

TODO(ziyu): implement. Tests: tests/exercises/test_ex6_reaper.py
"""

from datetime import datetime

from sqlalchemy.orm import Session

STALE_ERROR = "Timed out: worker did not finish (possible crash)"


def requeue_stale_jobs(db: Session, now: datetime, timeout_seconds: int) -> list[int]:
    """Find RUNNING jobs with started_at older than now - timeout_seconds.

    For each (lock rows with SELECT ... FOR UPDATE SKIP LOCKED, so two reapers
    cannot grab the same job):
      - attempts < max_attempts -> error = STALE_ERROR, transition to QUEUED;
                                   include its id in the returned list
      - otherwise              -> error = STALE_ERROR, transition to FAILED
    Commit once at the end. Return the ids to re-enqueue, ascending. The caller
    enqueues them AFTER this returns (never enqueue before the commit).
    """
    raise NotImplementedError("Exercise 6: requeue_stale_jobs()")
