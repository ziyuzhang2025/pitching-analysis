"""Import every model here so Alembic autogenerate and the app see them."""

from app.models.athlete import Athlete
from app.models.enums import JobStatus
from app.models.pipeline import AnalysisJob, Event, Pitch, TrainingSession, Video

__all__ = [
    "AnalysisJob",
    "Athlete",
    "Event",
    "JobStatus",
    "Pitch",
    "TrainingSession",
    "Video",
]
