"""WORKED EXAMPLE (agent-written): a complete resource with create, get, and a
paginated list. Copy these patterns for the exercise endpoints:

- Pydantic schemas validate input; handlers never trust raw data.
- The database enforces uniqueness; the handler turns IntegrityError into a 409.
- Lists use cursor pagination (fetch limit + 1 rows to know if there is a next page).
- Errors are raised as APIError subclasses and rendered in one JSON shape.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import Conflict, NotFound
from app.models import Athlete
from app.pagination import Page, clamp_limit, decode_cursor, next_cursor_for
from app.schemas import AthleteCreate, AthleteOut

router = APIRouter(prefix="/athletes", tags=["athletes"])


@router.post("", response_model=AthleteOut, status_code=status.HTTP_201_CREATED)
def create_athlete(payload: AthleteCreate, db: Session = Depends(get_db)) -> Athlete:
    athlete = Athlete(**payload.model_dump())
    db.add(athlete)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Checking "does it exist?" first would race with a concurrent request;
        # the unique constraint is the real guarantee.
        raise Conflict(f"Athlete code '{payload.code}' already exists") from exc
    db.refresh(athlete)
    return athlete


@router.get("/{athlete_id}", response_model=AthleteOut)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)) -> Athlete:
    athlete = db.get(Athlete, athlete_id)
    if athlete is None:
        raise NotFound("Athlete", athlete_id)
    return athlete


@router.get("", response_model=Page[AthleteOut])
def list_athletes(
    limit: int = Query(default=20),
    cursor: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Page[AthleteOut]:
    limit = clamp_limit(limit)
    after = decode_cursor(cursor)
    query = select(Athlete).order_by(Athlete.id).limit(limit + 1)
    if after is not None:
        query = query.where(Athlete.id > after)
    rows = list(db.scalars(query))
    return Page[AthleteOut](
        items=[AthleteOut.model_validate(a) for a in rows[:limit]],
        next_cursor=next_cursor_for(rows, limit),
    )
