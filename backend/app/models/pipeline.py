"""EXERCISE 1 (Ziyu): the rest of the data model.

TODO(ziyu): define these SQLAlchemy models here, following app/models/athlete.py,
then write migration 0002 (see docs/backend_exercises.md, Exercise 1). Tests:
tests/exercises/test_ex1_models.py.

Required classes and tables (column names are part of the contract):

TrainingSession  -> table "sessions"
    id PK; athlete_id FK athletes.id NOT NULL; recorded_on DATE NOT NULL;
    location VARCHAR(200) NULL; notes TEXT NULL; created_at timestamptz default now()

Video -> table "videos"
    id PK; session_id FK sessions.id NOT NULL; sha256 VARCHAR(64) NOT NULL;
    storage_key VARCHAR(200) NOT NULL UNIQUE; filename VARCHAR(255) NOT NULL;
    bytes BIGINT NOT NULL; fps FLOAT NULL; width INT NULL; height INT NULL;
    view VARCHAR(20) NULL (CHECK: NULL or one of app.models.enums.CAMERA_VIEWS);
    created_at timestamptz default now()
    UNIQUE (session_id, sha256)            <- same file in the same session = same video

AnalysisJob -> table "analysis_jobs"
    id PK; video_id FK videos.id NOT NULL; detector_version VARCHAR(40) NOT NULL;
    status VARCHAR(10) NOT NULL default 'queued' (CHECK: one of JobStatus values);
    attempts INT NOT NULL default 0; max_attempts INT NOT NULL default 3;
    idempotency_key VARCHAR(100) NULL UNIQUE; error TEXT NULL;
    queued_at timestamptz NOT NULL default now(); started_at timestamptz NULL;
    finished_at timestamptz NULL; worker_id VARCHAR(100) NULL
    INDEX (status, queued_at); INDEX (video_id, detector_version)
    PARTIAL UNIQUE INDEX "uq_analysis_jobs_active" ON (video_id, detector_version)
        WHERE status IN ('queued', 'running')   <- at most one active job per video+version

Pitch -> table "pitches"
    id PK; job_id FK analysis_jobs.id ON DELETE CASCADE NOT NULL; window_index INT NOT NULL;
    start_frame INT NOT NULL; end_frame INT NOT NULL; UNIQUE (job_id, window_index)

Event -> table "events"
    id PK; pitch_id FK pitches.id ON DELETE CASCADE NOT NULL; name VARCHAR(40) NOT NULL;
    frame INT NOT NULL; time_s FLOAT NOT NULL; method VARCHAR(10) NOT NULL default 'auto'
    (CHECK: one of EVENT_METHODS); confidence FLOAT NULL; INDEX (pitch_id, name)

Also add relationships you find useful (e.g. Pitch.events), and export every
class from app/models/__init__.py.
"""
