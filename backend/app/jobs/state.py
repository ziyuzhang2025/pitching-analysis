"""EXERCISE 2 (Ziyu): the job state machine and retry policy.

TODO(ziyu): implement everything marked TODO. These are pure functions on a job
object: no database calls, so they are easy to unit-test.
Tests: tests/exercises/test_ex2_state_machine.py

States: queued -> running -> succeeded | failed, plus running -> queued (retry or
crash recovery). succeeded and failed are terminal: a new analysis is a new job.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime
from typing import Any

from app.models.enums import JobStatus

MAX_ERROR_CHARS = 2000


class InvalidTransition(Exception):
    """Raised when a transition is not in ALLOWED_TRANSITIONS."""

    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot move job from {current} to {target}")
        self.current = current
        self.target = target


# TODO(ziyu): map each status to the set of statuses it may move to.
ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {}


def transition(job: Any, target: JobStatus, now: datetime) -> None:
    """Move job to target, or raise InvalidTransition. Side effects by target:

    - RUNNING:   attempts += 1, started_at = now, finished_at = None
    - QUEUED:    queued_at = now (a retry or crash recovery); started_at unchanged
    - SUCCEEDED: finished_at = now, error = None
    - FAILED:    finished_at = now
    job.status holds the string value (e.g. "running"). Compare using JobStatus(job.status).
    """
    raise NotImplementedError("Exercise 2: transition()")


def next_retry_delay(attempts: int, base: float, cap: float,
                     rng: Callable[[], float] = random.random) -> float:
    """Exponential backoff with full jitter, in seconds.

    ceiling = min(cap, base * 2 ** (attempts - 1)); return rng() * ceiling.
    attempts is the number of attempts already made (>= 1). rng returns [0, 1).
    Raise ValueError if attempts < 1.
    """
    raise NotImplementedError("Exercise 2: next_retry_delay()")


def handle_failure(job: Any, error: str, now: datetime, base: float, cap: float,
                   rng: Callable[[], float] = random.random) -> float | None:
    """Called when a RUNNING job's attempt fails.

    - Store error truncated to MAX_ERROR_CHARS in job.error.
    - If job.attempts < job.max_attempts: transition to QUEUED and return the retry
      delay from next_retry_delay(job.attempts, base, cap, rng).
    - Otherwise transition to FAILED and return None.
    """
    raise NotImplementedError("Exercise 2: handle_failure()")
