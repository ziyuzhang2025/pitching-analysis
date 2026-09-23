"""EXERCISE 5a (Ziyu): job status endpoints.

TODO(ziyu): implement. Tests: tests/exercises/test_ex5_worker_and_jobs.py

GET /jobs/{job_id} -> 200 JobOut, 404 if missing.
GET /jobs?status=<queued|running|succeeded|failed>&limit=&cursor= -> 200 Page[JobOut]
    Ordered by id; the optional status filter; cursor pagination like athletes.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotImplementedYet
from app.pagination import Page
from app.schemas import JobOut, JobStatusLiteral

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    raise NotImplementedYet("Exercise 5a: GET /jobs/{id}")


@router.get("", response_model=Page[JobOut])
def list_jobs(
    status: JobStatusLiteral | None = Query(default=None),
    limit: int = Query(default=20),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    raise NotImplementedYet("Exercise 5a: GET /jobs")
