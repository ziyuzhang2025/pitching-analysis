"""EXERCISE 7a (Ziyu): versioned analysis results.

TODO(ziyu): implement. Tests: tests/exercises/test_ex7_results_and_backfill.py

GET /videos/{video_id}/results?detector_version=<optional>
    - 404 (code "not_found") if the video does not exist.
    - Pick the most recent SUCCEEDED job for this video (highest finished_at, then id),
      restricted to detector_version if given.
    - 404 (code "no_results") if there is no such job.
    - 200 ResultsOut: pitches ordered by window_index; events ordered by frame.
    - Avoid N+1 queries: load pitches and events with selectinload.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotImplementedYet
from app.schemas import ResultsOut

router = APIRouter(tags=["results"])


@router.get("/videos/{video_id}/results", response_model=ResultsOut)
def get_results(
    video_id: int,
    detector_version: str | None = Query(default=None, max_length=40),
    db: Session = Depends(get_db),
):
    raise NotImplementedYet("Exercise 7a: GET /videos/{id}/results")
