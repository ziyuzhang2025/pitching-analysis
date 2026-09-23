"""EXERCISE 3a (Ziyu): training sessions for an athlete.

TODO(ziyu): implement both handlers following app/api/athletes.py.
Tests: tests/exercises/test_ex3_sessions_videos_api.py

POST /athletes/{athlete_id}/sessions  body SessionCreate -> 201 SessionOut
    404 if the athlete does not exist.
GET  /athletes/{athlete_id}/sessions?limit=&cursor=  -> 200 Page[SessionOut]
    404 if the athlete does not exist; sessions ordered by id; cursor pagination.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import NotImplementedYet
from app.pagination import Page
from app.schemas import SessionCreate, SessionOut

router = APIRouter(prefix="/athletes/{athlete_id}/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(athlete_id: int, payload: SessionCreate, db: Session = Depends(get_db)):
    raise NotImplementedYet("Exercise 3a: POST /athletes/{id}/sessions")


@router.get("", response_model=Page[SessionOut])
def list_sessions(
    athlete_id: int,
    limit: int = Query(default=20),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    raise NotImplementedYet("Exercise 3a: GET /athletes/{id}/sessions")
