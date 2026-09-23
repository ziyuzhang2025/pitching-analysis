"""EXERCISE 4 (Ziyu): idempotent video creation and job submission.

The rule: the DATABASE guarantees uniqueness (unique constraints, the partial unique
index on active jobs). Application code must still handle the race where two requests
both pass a "does it exist?" check: catch IntegrityError, roll back, and load the row
the other request created.

TODO(ziyu): implement both functions. Tests: tests/exercises/test_ex4_idempotency.py
"""

from typing import Any

from sqlalchemy.orm import Session

from app.storage import StoredFile


def find_or_create_video(db: Session, session_id: int, stored: StoredFile, filename: str,
                         view: str | None) -> tuple[Any, bool]:
    """Return (video, created).

    If a video with (session_id, stored.sha256) exists, return (existing, False).
    Otherwise insert Video(session_id, sha256, storage_key=stored.key, filename,
    bytes=stored.size, view), commit, and return (new, True).
    On IntegrityError (a concurrent upload of the same file won the race):
    roll back and return (the winner's row, False).
    The caller deletes the stored file when created is False.
    """
    raise NotImplementedError("Exercise 4: find_or_create_video()")


def get_or_create_job(db: Session, video_id: int, detector_version: str,
                      idempotency_key: str | None, max_attempts: int) -> tuple[Any, bool]:
    """Return (job, created). Does NOT enqueue: the caller enqueues after commit.

    1. If idempotency_key is given and a job with that key exists:
         - if it belongs to a different video_id -> raise app.errors.Conflict
         - else return (that job, False)
    2. If an ACTIVE job (queued/running) exists for (video_id, detector_version),
       return (it, False).
    3. Otherwise insert a queued job (with the key, if any), commit, return (job, True).
    4. On IntegrityError: roll back and repeat steps 1-2 (the other request won);
       if still nothing is found, re-raise.
    """
    raise NotImplementedError("Exercise 4: get_or_create_job()")
