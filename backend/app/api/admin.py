"""EXERCISE 7b (Ziyu): backfill after a detector upgrade.

TODO(ziyu): implement. Tests: tests/exercises/test_ex7_results_and_backfill.py

POST /admin/reanalyze?detector_version=<optional; default get_analyzer().version>
    - For every video WITHOUT a succeeded job at that version, and WITHOUT an active
      (queued/running) job at that version, create a queued job (reuse
      get_or_create_job so a race with /analyze cannot create duplicates).
    - Commit, then enqueue each new job id.
    - 202 ReanalyzeOut(detector_version, enqueued=<count>, job_ids=<new ids, ascending>).
    - Calling it twice in a row must enqueue nothing the second time.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotImplementedYet
from app.schemas import ReanalyzeOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reanalyze", response_model=ReanalyzeOut, status_code=status.HTTP_202_ACCEPTED)
def reanalyze(
    detector_version: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
):
    raise NotImplementedYet("Exercise 7b: POST /admin/reanalyze")
