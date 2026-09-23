# PitchLab API

An async backend around the pitching timing analyzer: upload a video, get
versioned event timings back. It is built to practise and show backend engineering
(API design, relational modeling, job queues, idempotency, crash recovery, testing,
Docker, CI, load testing). The plan is `docs/RESEARCH_GUIDE.md`, Phase 8.

> **Status:** the scaffold, the worked example, and the infrastructure are done. The core
> features are **exercises Ziyu implements** (`docs/backend_exercises.md`). Until then,
> those endpoints return `501 not_implemented`. Check progress with
> `python scripts/progress.py`.

## Architecture

```
Client ──► FastAPI (api) ──► PostgreSQL   athletes → sessions → videos → analysis_jobs → pitches → events
              │  enqueue job_id
              ▼
            Redis ──► worker × N ──► analyzer (FakeAnalyzer, or the repo's real scripts)
                          │
                          └──► /data/storage (LocalStorage behind a Storage interface)
```

- The **database is the source of truth**; the queue only carries job ids.
- Jobs move `queued → running → succeeded | failed` (with retries, backoff, and a reaper).
- Every result is tied to the `detector_version` that produced it.

## Quick start (Docker)

```bash
cd backend
docker compose up --build            # postgres, redis, migrate, api, worker
open http://localhost:8000/docs      # interactive OpenAPI docs
docker compose up --build --scale worker=4
```

The worker uses the **fake analyzer** by default (it returns fixed events after
`FAKE_ANALYZER_SECONDS`). To run the real analyzer in Docker, set
`INSTALL_ANALYZER=true ANALYZER=real`. Results from Docker are **not** comparable with
the Mac research numbers (different MediaPipe build).

## Local development (without Docker for the app)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
docker compose up -d postgres redis          # or local installs
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload                # terminal 1
python -m worker.run                         # terminal 2
```

## Tests

```bash
pytest -m "not ziyu"          # everything except the exercises (must stay green)
python scripts/progress.py    # exercise checklist
pytest tests/exercises/test_ex2_state_machine.py -x   # work on one exercise
```

Tests use a real Postgres (`TEST_DATABASE_URL`, default database `pitchlab_test`, which
is created automatically) and Redis db 15 (`TEST_REDIS_URL`).

## Load test

```bash
pip install -r loadtest/requirements.txt
python loadtest/run_scaling.py --mode compose --workers 1,2,4 --analyzer-seconds 3
```

This writes `loadtest/results/<timestamp>/summary.md` with jobs/min, job end-to-end p50/p95,
API p50/p95, and error rate for each worker count.

## Configuration

All settings are environment variables (see `.env.example` and `app/config.py`):
`DATABASE_URL`, `REDIS_URL`, `STORAGE_DIR`, `MAX_UPLOAD_BYTES`, `ANALYZER`
(`fake`|`real`), `FAKE_ANALYZER_SECONDS`, `JOB_MAX_ATTEMPTS`, `JOB_TIMEOUT_SECONDS`,
`RETRY_BASE_SECONDS`, `RETRY_CAP_SECONDS`, `LOG_LEVEL`.

## Layout

| Path | What | Written by |
|---|---|---|
| `app/config.py`, `db.py`, `logging.py`, `errors.py`, `pagination.py`, `storage.py`, `queue.py`, `analyzers.py`, `main.py` | Infrastructure | Claude |
| `app/models/athlete.py`, `app/api/athletes.py`, `app/api/health.py`, `migrations/versions/0001_*` | Worked example | Claude |
| `app/models/pipeline.py`, `migrations/versions/0002_*` | Exercise 1 | **Ziyu** |
| `app/jobs/state.py` | Exercise 2 | **Ziyu** |
| `app/api/sessions.py`, `app/api/videos.py` | Exercises 3–4 | **Ziyu** |
| `app/services/idempotency.py` | Exercise 4 | **Ziyu** |
| `worker/tasks.py`, `app/api/jobs.py` | Exercise 5 | **Ziyu** |
| `app/jobs/reaper.py` | Exercise 6 | **Ziyu** |
| `app/api/results.py`, `app/api/admin.py` | Exercise 7 | **Ziyu** |
| `worker/run.py`, `loadtest/`, `scripts/`, Docker, CI | Tooling | Claude |

Who wrote what, in detail: `docs/backend_ownership.md`.
