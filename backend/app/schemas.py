"""Request/response schemas: the API contract. Exercise tests assert these shapes."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ThrowingHand = Literal["right", "left"]
CameraView = Literal["arm_side", "glove_side", "behind", "rear_oblique", "front", "other"]
JobStatusLiteral = Literal["queued", "running", "succeeded", "failed"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Athletes (worked example) ---------------------------------------------------
class AthleteCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    throwing_hand: ThrowingHand
    height_m: float | None = Field(default=None, gt=1.0, lt=2.5)


class AthleteOut(ORMModel):
    id: int
    code: str
    throwing_hand: ThrowingHand
    height_m: float | None
    created_at: datetime


# --- Sessions (Exercise 3) --------------------------------------------------------
class SessionCreate(BaseModel):
    recorded_on: date
    location: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class SessionOut(ORMModel):
    id: int
    athlete_id: int
    recorded_on: date
    location: str | None
    notes: str | None
    created_at: datetime


# --- Videos (Exercise 3) ----------------------------------------------------------
class VideoOut(ORMModel):
    id: int
    session_id: int
    sha256: str
    filename: str
    bytes: int
    fps: float | None
    width: int | None
    height: int | None
    view: CameraView | None
    created_at: datetime


# --- Jobs (Exercises 4-5) ---------------------------------------------------------
class JobOut(ORMModel):
    id: int
    video_id: int
    detector_version: str
    status: JobStatusLiteral
    attempts: int
    max_attempts: int
    error: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


# --- Results (Exercise 7) ---------------------------------------------------------
class EventOut(ORMModel):
    name: str
    frame: int
    time_s: float
    method: str
    confidence: float | None


class PitchOut(ORMModel):
    window_index: int
    start_frame: int
    end_frame: int
    events: list[EventOut]


class ResultsOut(BaseModel):
    video_id: int
    job_id: int
    detector_version: str
    pitches: list[PitchOut]


class ReanalyzeOut(BaseModel):
    detector_version: str
    enqueued: int
    job_ids: list[int]


# --- System -----------------------------------------------------------------------
class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    redis: bool


class VersionOut(BaseModel):
    api_version: str
    detector_version: str
    analyzer: str
