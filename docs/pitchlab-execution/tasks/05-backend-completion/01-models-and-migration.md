# 05.01 — Implement models and migration

Status: ACTIVE — system gate verified; capability gate pending. Implementation was explicitly delegated to Codex and attributed in the ownership log.
Dependency: 2026-10-14 evidence preflight recorded. Disposable PostgreSQL is required for the system gate.

## Scope and authorized files

- Modify `backend/app/models/pipeline.py`.
- Modify `backend/app/models/__init__.py`.
- Create one `backend/migrations/versions/0002_*.py` migration.
- Do not change exercise tests to make implementation pass.
- Do not implement API, state-machine or worker behavior in this task.

Read [exercise specification](../../../backend_exercises.md), `backend/app/models/athlete.py`, the target docstring and `backend/tests/exercises/test_ex1_models.py`. Later exercises import these exact model names and fields.

## Interfaces and invariants

Export `TrainingSession`, `Video`, `AnalysisJob`, `Pitch` and `Event` from `app.models`. Match the table and column contract in `pipeline.py` exactly.

Database-enforced invariants:

- one `(session_id, sha256)` video record per session;
- globally unique `storage_key` and nullable globally unique `idempotency_key`;
- only valid camera views, job statuses and event methods;
- at most one queued/running job per `(video_id, detector_version)` using the named partial unique index `uq_analysis_jobs_active`;
- one pitch window index per job;
- deleting a job cascades to pitches and events;
- migration metadata and SQLAlchemy metadata have no diff.

## Required outcome / system gate
Existing exercise assertions pass, constraints hold, disposable migration upgrade/downgrade/upgrade verified.

## Capability gate
Explain partial uniqueness, foreign keys and migration data loss.

## Execution steps

- [x] Start disposable PostgreSQL/Redis only; confirm the configured test database may be destroyed. The fixtures drop the `public` schema and flush Redis DB 15.
- [x] From `backend/`, install `requirements-dev.txt` in the backend environment.
- [x] Run `pytest tests/exercises/test_ex1_models.py -x`; record the expected initial failure caused by missing exports/models/migration.
- [x] Implement the five SQLAlchemy models and exports, following the existing typed model style.
- [x] Generate migration `0002`, then read and correct it. Confirm the partial-index predicate and downgrade order explicitly.
- [x] Run `alembic upgrade head`, `alembic downgrade 0001`, then `alembic upgrade head` against the disposable database.
- [x] Run `pytest tests/exercises/test_ex1_models.py -x`.
- [x] Run `pytest -m "not ziyu"`, `ruff check .`, and `mypy` from `backend/`.
- [x] Review the diff. Confirm only the three authorized implementation targets changed and no generated secrets or database files were added.
- [ ] Record Ziyu's independent explanation in the ownership log. The verification commands and delegated authorship are recorded; system and capability gates are separate.

## Failure scenarios that must be demonstrated

- inserting a second active job for the same video/version raises `IntegrityError`;
- a succeeded job does not prevent a new active job for the same video/version;
- an invalid camera view or job status is rejected by PostgreSQL;
- deleting a job deletes its pitches and events;
- downgrade removes only the five new tables and upgrade recreates them.

Evidence destination: [verification log](../../evidence/verification-log.md).

## 2026-10-19 gate status

- System gate: VERIFIED — 19/19 focused tests passed; migration downgrade/upgrade
  completed; 26/26 non-exercise tests, Ruff, and mypy passed.
- Capability gate: PENDING — Ziyu must independently explain partial uniqueness,
  foreign-key cascades, and why destructive downgrades require explicit data-loss review.

Stop before destructive fixtures if the services are not explicitly disposable. If Docker remains unavailable, code review may proceed but the system gate remains BLOCKED. Do not mark complete from inspection, SQLite checks or model import alone.
