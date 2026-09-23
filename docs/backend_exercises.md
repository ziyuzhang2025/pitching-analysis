# Backend exercises (Ziyu)

You write these. Claude explains concepts, answers questions, and reviews your diffs,
but does not write the implementations unless you say "write it for me" for a
specific item (that gets recorded in `docs/backend_ownership.md`).

**How to work**
1. Do the exercises in order; later ones build on earlier ones.
2. Read the docstring in the target file. It is the spec.
3. Run that exercise's tests until they pass:
   `pytest tests/exercises/test_exN_*.py -x`
4. Run `pytest -m "not ziyu"` (must stay green) and `ruff check . && mypy`.
5. Commit. Ask Claude for a review and the defense questions.
6. Note what you learned in `docs/backend_ownership.md`.

Setup once: `docker compose up -d postgres redis`, then `pip install -r requirements-dev.txt`.

---

## Exercise 1: data model and migration (19 tests)

**Files:** `app/models/pipeline.py`, `app/models/__init__.py`, new `migrations/versions/0002_*.py`

**Learn:** SQLAlchemy 2.0 typed models (`Mapped`, `mapped_column`), foreign keys, unique
and CHECK constraints, **partial unique indexes**, `ON DELETE CASCADE`, and Alembic.

**Steps:**
1. Write the five models from the docstring, copying the style of `app/models/athlete.py`.
2. Generate the migration, then **read and fix it** (autogenerate is a draft, not an answer):
   `alembic revision --autogenerate -m "pipeline tables" --rev-id 0002`
3. `alembic upgrade head`, then `alembic downgrade 0001`, then `upgrade head` again.

**Hints:** the partial unique index is
`Index("uq_analysis_jobs_active", "video_id", "detector_version", unique=True, postgresql_where=text("status IN ('queued', 'running')"))`.
Why is it partial and not a normal unique constraint? Answer that in ADR 2.

**Defense:** Why enforce uniqueness in the database and not just in Python? What happens
to pitches when a job is deleted, and why is that the right choice here?

## Exercise 2: state machine and retry policy (19 tests)

**File:** `app/jobs/state.py` (pure functions, no database)

**Learn:** modeling a lifecycle as explicit states and transitions; exponential backoff
with **full jitter**, and why jitter prevents retry storms.

**Defense:** What goes wrong if 500 failed jobs all retry after exactly 2, 4, 8 seconds?
Why are `succeeded` and `failed` terminal?

## Exercise 3: sessions and uploads (11 tests)

**Files:** `app/api/sessions.py`, `app/api/videos.py` (upload + get)

**Learn:** nested REST resources, 404s for parent resources, multipart uploads streamed
to disk (never `await file.read()` on a 500 MB video), status codes 201/200/404/413/415/422.

**Defense:** Why stream the upload instead of reading it into memory? Why hash while streaming?

## Exercise 4: idempotency and races (7 tests)

**Files:** `app/services/idempotency.py`, `app/api/videos.py` (`/analyze`)

**Learn:** idempotent APIs, the `Idempotency-Key` header, **check-then-insert races**, and
recovering from `IntegrityError`. Commit to the DB first, enqueue second.

The two race tests start 8 threads at the same instant. A version without the
`IntegrityError` handling fails them (Claude checked this with a deliberately naive version).

**Defense:** Walk through two parallel `/analyze` calls line by line. Why must
`enqueue_analysis` come *after* `commit`? What if Redis is down at that moment?

## Exercise 5: worker task and job API (8 tests)

**Files:** `worker/tasks.py`, `app/api/jobs.py`

**Learn:** transaction boundaries, row locks (`SELECT ... FOR UPDATE`), at-least-once
delivery (a queue message can arrive twice), keeping slow work outside transactions,
and atomic result writes.

**Defense:** Where are your transaction boundaries and why? What happens if the same job
id is delivered twice? If the worker crashes after writing half the pitches?

## Exercise 6: crash recovery (3 tests)

**File:** `app/jobs/reaper.py` (already called every 60 s by `worker/run.py`)

**Learn:** timeouts as failure detection, `FOR UPDATE SKIP LOCKED` so several reapers
can run safely.

**Defense:** A worker is merely slow, not dead. What does the reaper do, and how could
you avoid double work? (Hint: heartbeats; describe them, no need to build.)

## Exercise 7: versioned results and backfill (5 tests)

**Files:** `app/api/results.py`, `app/api/admin.py`

**Learn:** avoiding N+1 queries (`selectinload`), `NOT EXISTS` subqueries, data backfills
after a model/version change.

**Defense:** Detector 1.1 ships. How do clients keep getting consistent results while the
backfill runs? How would you backfill 1 million videos without flooding the queue?

---

## After all exercises

1. `python scripts/progress.py` shows 7/7 done; CI is green.
2. Coverage of `app/` is at least 80%: `pytest --cov`.
3. Run the load test on your Mac (`loadtest/run_scaling.py --mode compose`) and put the
   table into `backend/README.md`.
4. Write the 5 ADRs (`docs/adr/`).
5. Defense check with Claude: all 8 questions in `docs/RESEARCH_GUIDE.md` §8.10.
6. After that, ask Claude for the reference implementation to compare approaches.

**Official docs to read alongside:** SQLAlchemy 2.0 ORM Quick Start; Alembic tutorial
("Auto Generating Migrations"); FastAPI tutorial ("Request Files", "Dependencies");
PostgreSQL docs on partial indexes and `SELECT ... FOR UPDATE SKIP LOCKED`; RQ docs
("Jobs", "Scheduling").
