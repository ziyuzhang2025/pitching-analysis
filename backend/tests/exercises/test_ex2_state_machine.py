"""Exercise 2: job state machine and retry policy (pure unit tests)."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.jobs import state
from app.models.enums import JobStatus

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 10, 1, 12, 5, tzinfo=timezone.utc)


def job(status="queued", attempts=0, max_attempts=3):
    return SimpleNamespace(status=status, attempts=attempts, max_attempts=max_attempts,
                           queued_at=None, started_at=None, finished_at=None, error=None)


def test_allowed_transitions_table():
    Q, R, S, F = JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCEEDED, JobStatus.FAILED
    expected = {Q: {R}, R: {S, F, Q}, S: set(), F: set()}
    assert state.ALLOWED_TRANSITIONS == expected


def test_start_running():
    j = job()
    state.transition(j, JobStatus.RUNNING, NOW)
    assert (j.status, j.attempts, j.started_at, j.finished_at) == ("running", 1, NOW, None)


def test_succeed_clears_error():
    j = job(status="running", attempts=1)
    j.error = "old"
    state.transition(j, JobStatus.SUCCEEDED, LATER)
    assert (j.status, j.finished_at, j.error) == ("succeeded", LATER, None)


def test_requeue_sets_queued_at():
    j = job(status="running", attempts=1)
    j.started_at = NOW
    state.transition(j, JobStatus.QUEUED, LATER)
    assert (j.status, j.queued_at, j.started_at) == ("queued", LATER, NOW)


@pytest.mark.parametrize("current,target", [
    ("queued", "succeeded"), ("queued", "failed"), ("succeeded", "running"),
    ("failed", "queued"), ("succeeded", "queued"), ("running", "running"),
])
def test_illegal_transitions_raise(current, target):
    j = job(status=current)
    with pytest.raises(state.InvalidTransition):
        state.transition(j, JobStatus(target), NOW)
    assert j.status == current  # unchanged


@pytest.mark.parametrize("attempts,expected", [(1, 2.0), (2, 4.0), (3, 8.0), (10, 300.0)])
def test_backoff_ceiling_with_max_jitter(attempts, expected):
    assert state.next_retry_delay(attempts, base=2.0, cap=300.0, rng=lambda: 1.0) == expected


def test_backoff_full_jitter_range():
    assert state.next_retry_delay(3, base=2.0, cap=300.0, rng=lambda: 0.0) == 0.0
    assert state.next_retry_delay(3, base=2.0, cap=300.0, rng=lambda: 0.5) == 4.0
    for _ in range(200):
        assert 0.0 <= state.next_retry_delay(4, 2.0, 300.0) <= 16.0


def test_backoff_rejects_zero_attempts():
    with pytest.raises(ValueError):
        state.next_retry_delay(0, 2.0, 300.0)


def test_failure_with_attempts_left_requeues():
    j = job(status="running", attempts=1, max_attempts=3)
    delay = state.handle_failure(j, "boom", NOW, base=2.0, cap=300.0, rng=lambda: 1.0)
    assert delay == 2.0
    assert (j.status, j.error, j.queued_at) == ("queued", "boom", NOW)


def test_failure_on_last_attempt_fails():
    j = job(status="running", attempts=3, max_attempts=3)
    assert state.handle_failure(j, "boom", NOW, base=2.0, cap=300.0) is None
    assert (j.status, j.finished_at, j.error) == ("failed", NOW, "boom")


def test_error_is_truncated():
    j = job(status="running", attempts=3)
    state.handle_failure(j, "x" * 5000, NOW, base=2.0, cap=300.0)
    assert len(j.error) == state.MAX_ERROR_CHARS
