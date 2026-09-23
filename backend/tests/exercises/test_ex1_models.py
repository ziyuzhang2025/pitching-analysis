"""Exercise 1: models + migration 0002."""

from datetime import date

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError

from tests.exercises.helpers import need

EXPECTED_COLUMNS = {
    "sessions": {"id", "athlete_id", "recorded_on", "location", "notes", "created_at"},
    "videos": {"id", "session_id", "sha256", "storage_key", "filename", "bytes", "fps",
               "width", "height", "view", "created_at"},
    "analysis_jobs": {"id", "video_id", "detector_version", "status", "attempts",
                      "max_attempts", "idempotency_key", "error", "queued_at", "started_at",
                      "finished_at", "worker_id"},
    "pitches": {"id", "job_id", "window_index", "start_frame", "end_frame"},
    "events": {"id", "pitch_id", "name", "frame", "time_s", "method", "confidence"},
}


@pytest.fixture
def inspector(clean_db):
    engine = create_engine(clean_db)
    yield inspect(engine)
    engine.dispose()


def test_models_are_exported():
    for name in ["TrainingSession", "Video", "AnalysisJob", "Pitch", "Event"]:
        need("app.models", name)


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_migration_creates_table_with_columns(inspector, table):
    assert table in inspector.get_table_names(), f"migration 0002 must create {table}"
    columns = {c["name"] for c in inspector.get_columns(table)}
    assert EXPECTED_COLUMNS[table] <= columns


def test_nullability(inspector):
    cols = {c["name"]: c for c in inspector.get_columns("analysis_jobs")}
    assert not cols["status"]["nullable"] and not cols["attempts"]["nullable"]
    assert cols["idempotency_key"]["nullable"] and cols["started_at"]["nullable"]
    vcols = {c["name"]: c for c in inspector.get_columns("videos")}
    assert not vcols["sha256"]["nullable"] and vcols["fps"]["nullable"]


def _unique_sets(inspector, table):
    sets = [tuple(sorted(u["column_names"])) for u in inspector.get_unique_constraints(table)]
    sets += [tuple(sorted(i["column_names"])) for i in inspector.get_indexes(table)
             if i.get("unique") and not i.get("dialect_options", {}).get("postgresql_where")]
    return set(sets)


def test_unique_constraints(inspector):
    assert ("session_id", "sha256") in _unique_sets(inspector, "videos")
    assert ("storage_key",) in _unique_sets(inspector, "videos")
    assert ("idempotency_key",) in _unique_sets(inspector, "analysis_jobs")
    assert ("job_id", "window_index") in _unique_sets(inspector, "pitches")


def test_indexes(inspector):
    job_indexes = [i["column_names"] for i in inspector.get_indexes("analysis_jobs")]
    assert ["status", "queued_at"] in job_indexes
    assert ["video_id", "detector_version"] in job_indexes
    assert ["pitch_id", "name"] in [i["column_names"] for i in inspector.get_indexes("events")]


def test_foreign_keys_and_cascades(inspector):
    fks = {fk["constrained_columns"][0]: fk for fk in inspector.get_foreign_keys("pitches")}
    assert fks["job_id"]["referred_table"] == "analysis_jobs"
    assert fks["job_id"]["options"].get("ondelete", "").upper() == "CASCADE"
    efks = {fk["constrained_columns"][0]: fk for fk in inspector.get_foreign_keys("events")}
    assert efks["pitch_id"]["options"].get("ondelete", "").upper() == "CASCADE"


def _seed(db, status="queued"):
    Athlete = need("app.models", "Athlete")
    TrainingSession = need("app.models", "TrainingSession")
    Video = need("app.models", "Video")
    AnalysisJob = need("app.models", "AnalysisJob")
    athlete = Athlete(code="P01", throwing_hand="right")
    db.add(athlete)
    db.flush()
    session = TrainingSession(athlete_id=athlete.id, recorded_on=date(2026, 10, 1))
    db.add(session)
    db.flush()
    video = Video(session_id=session.id, sha256="a" * 64, storage_key="k1.mp4",
                  filename="clip.mp4", bytes=10)
    db.add(video)
    db.flush()
    job = AnalysisJob(video_id=video.id, detector_version="1.0.0", status=status)
    db.add(job)
    db.commit()
    return video, job


def test_defaults(db):
    _, job = _seed(db)
    db.refresh(job)
    assert job.status == "queued" and job.attempts == 0 and job.max_attempts == 3
    assert job.queued_at is not None and job.error is None


@pytest.mark.parametrize("field,value", [("status", "paused")])
def test_status_check_constraint(db, field, value):
    _, job = _seed(db)
    setattr(job, field, value)
    with pytest.raises(IntegrityError):
        db.commit()


def test_view_check_constraint(db):
    video, _ = _seed(db)
    video.view = "sideways"
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_file_twice_in_session_rejected(db):
    Video = need("app.models", "Video")
    video, _ = _seed(db)
    db.add(Video(session_id=video.session_id, sha256=video.sha256, storage_key="k2.mp4",
                 filename="again.mp4", bytes=10))
    with pytest.raises(IntegrityError):
        db.commit()


def test_only_one_active_job_per_video_and_version(db):
    AnalysisJob = need("app.models", "AnalysisJob")
    video, first = _seed(db)
    db.add(AnalysisJob(video_id=video.id, detector_version="1.0.0", status="queued"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    first.status = "succeeded"
    db.commit()
    db.add(AnalysisJob(video_id=video.id, detector_version="1.0.0", status="queued"))
    db.add(AnalysisJob(video_id=video.id, detector_version="1.1.0", status="queued"))
    db.commit()  # finished jobs and other versions do not block


def test_deleting_job_cascades_to_pitches_and_events(db):
    Pitch = need("app.models", "Pitch")
    Event = need("app.models", "Event")
    _, job = _seed(db)
    pitch = Pitch(job_id=job.id, window_index=1, start_frame=0, end_frame=100)
    db.add(pitch)
    db.flush()
    db.add(Event(pitch_id=pitch.id, name="ball_release", frame=50, time_s=0.2))
    db.commit()
    db.delete(job)
    db.commit()
    assert db.query(Pitch).count() == 0 and db.query(Event).count() == 0


def test_event_method_defaults_to_auto(db):
    Pitch = need("app.models", "Pitch")
    Event = need("app.models", "Event")
    _, job = _seed(db)
    pitch = Pitch(job_id=job.id, window_index=1, start_frame=0, end_frame=100)
    db.add(pitch)
    db.flush()
    event = Event(pitch_id=pitch.id, name="ball_release", frame=50, time_s=0.2)
    db.add(event)
    db.commit()
    db.refresh(event)
    assert event.method == "auto"


def test_migrations_match_models(clean_db):
    """`alembic revision --autogenerate` would find nothing: migration == models."""
    need("app.models", "AnalysisJob")
    from alembic.autogenerate import compare_metadata
    from alembic.migration import MigrationContext

    import app.models  # noqa: F401
    from app.db import Base

    engine = create_engine(clean_db)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    engine.dispose()
    assert diff == [], f"models and migrations differ: {diff}"


def test_migration_0002_downgrades_to_0001(clean_db, inspector):
    from tests.conftest import run_migrations

    assert "analysis_jobs" in inspector.get_table_names(), "write migration 0002 first"

    run_migrations(clean_db, "0001", downgrade=True)
    engine = create_engine(clean_db)
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    run_migrations(clean_db, "head")
    assert "athletes" in tables and not ({"sessions", "videos", "analysis_jobs"} & tables)
