"""Import every model here so Alembic autogenerate and the app see them."""

from app.models.athlete import Athlete
from app.models.enums import JobStatus

__all__ = ["Athlete", "JobStatus"]

# TODO(ziyu) Exercise 1: also import and export TrainingSession, Video, AnalysisJob,
# Pitch, Event from app.models.pipeline, e.g.
#   from app.models.pipeline import AnalysisJob, Event, Pitch, TrainingSession, Video
