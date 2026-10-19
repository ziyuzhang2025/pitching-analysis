"""Sessions, videos, analysis jobs, pitches, and detected events."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class TrainingSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    videos: Mapped[list[Video]] = relationship(back_populates="session")


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        CheckConstraint(
            "view IS NULL OR view IN "
            "('arm_side', 'glove_side', 'behind', 'rear_oblique', 'front', 'other')",
            name="view",
        ),
        UniqueConstraint("session_id", "sha256"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    view: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    session: Mapped[TrainingSession] = relationship(back_populates="videos")
    jobs: Mapped[list[AnalysisJob]] = relationship(back_populates="video")


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')", name="status"
        ),
        Index("ix_analysis_jobs_status_queued_at", "status", "queued_at"),
        Index(
            "ix_analysis_jobs_video_id_detector_version", "video_id", "detector_version"
        ),
        Index(
            "uq_analysis_jobs_active",
            "video_id",
            "detector_version",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(10), server_default="queued", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, server_default="3", nullable=False)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    worker_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    video: Mapped[Video] = relationship(back_populates="jobs")
    pitches: Mapped[list[Pitch]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )


class Pitch(Base):
    __tablename__ = "pitches"
    __table_args__ = (UniqueConstraint("job_id", "window_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False
    )
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_frame: Mapped[int] = mapped_column(Integer, nullable=False)
    end_frame: Mapped[int] = mapped_column(Integer, nullable=False)

    job: Mapped[AnalysisJob] = relationship(back_populates="pitches")
    events: Mapped[list[Event]] = relationship(
        back_populates="pitch", cascade="all, delete-orphan", passive_deletes=True
    )


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("method IN ('auto', 'manual')", name="method"),
        Index("ix_events_pitch_id_name", "pitch_id", "name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    pitch_id: Mapped[int] = mapped_column(
        ForeignKey("pitches.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    frame: Mapped[int] = mapped_column(Integer, nullable=False)
    time_s: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(10), server_default="auto", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    pitch: Mapped[Pitch] = relationship(back_populates="events")
