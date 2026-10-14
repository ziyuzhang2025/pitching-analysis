# Backend architecture: read before execution

Source inspection: 2026-10-13. This explains the current code and intended exercise contracts, not a verified running service. Recheck source before implementing. [Current state](02-current-state.md) owns verification status; [milestones](03-milestones.md) own scheduling.

## 1. The system in plain language

The backend manages recorded videos and the work needed to analyze them. FastAPI accepts requests, PostgreSQL stores authoritative records, local storage holds video bytes, and Redis/RQ dispatches analysis work to a separate worker process. A worker calls the existing Python analyzer scripts and is intended to save results back to PostgreSQL.

This is one backend application with separate API and worker entry points, sharing models, configuration and database. Multiple containers do not make it a collection of independent microservices. Keep this structure for the current scope.

There are currently two paths:

```text
EXISTING LOCAL UI PATH
Streamlit app.py → subprocess → detector scripts → local reports/plots/videos

INTENDED BACKEND PATH (core exercise implementations missing)
Client → FastAPI → PostgreSQL: metadata + job records
           │
           ├── LocalStorage: uploaded video bytes
           │
           └── Redis/RQ: job ID + request metadata
                        │
                     Worker → analyzer adapter → detector scripts
                        │
                        └── PostgreSQL: pitch/event results
```

The current Streamlit UI uses local subprocesses; it is not already a frontend for the API. M6 connects the paths. Durable backend plots, overlays, correction history and artifact APIs are planned additions.

## 2. Folder map and responsibilities

Paths below are relative to the repository root. **Implemented** means a function body exists and was inspected; it does not mean its integration has been run successfully.

```text
backend/
├── app/
│   ├── main.py                  # FastAPI factory, middleware, router registration
│   ├── config.py                # Environment-derived settings
│   ├── db.py                    # SQLAlchemy Base, engine, per-request sessions
│   ├── schemas.py               # Validated API input/output shapes
│   ├── errors.py                # Shared HTTP error representation
│   ├── logging.py               # JSON logs and request ID middleware
│   ├── pagination.py            # Cursor/limit helpers
│   ├── storage.py               # Storage interface and local streaming implementation
│   ├── queue.py                 # RQ enqueue and delayed retry transport
│   ├── analyzers.py             # Fake/real analyzer adapters
│   ├── api/
│   │   ├── athletes.py         # Implemented worked example
│   │   ├── health.py           # Implemented health/version handlers
│   │   ├── sessions.py         # Exercise handlers
│   │   ├── videos.py           # Exercise upload/get/analyze handlers
│   │   ├── jobs.py             # Exercise job status/list handlers
│   │   ├── results.py          # Exercise versioned-result handler
│   │   └── admin.py            # Exercise reanalysis/backfill handler
│   ├── models/
│   │   ├── athlete.py          # Implemented SQLAlchemy model
│   │   ├── pipeline.py         # Specifications only: five missing models
│   │   └── enums.py            # Shared allowed values
│   ├── services/idempotency.py # Exercise helpers for race-safe creation
│   └── jobs/
│       ├── state.py            # Exercise transitions/retry policy
│       └── reaper.py           # Exercise stale-job recovery
├── worker/
│   ├── run.py                  # Implemented RQ runner, scheduler, reaper thread
│   └── tasks.py                # Exercise run_analysis_job implementation
├── migrations/                 # Alembic; only 0001 athletes migration exists
├── tests/                      # Infrastructure and exercise tests
├── scripts/progress.py         # Runs exercise tests and reports progress
├── loadtest/                   # Locust workload and worker-scaling runner
├── Dockerfile.api
├── Dockerfile.worker
└── docker-compose.yml          # Postgres, Redis, migrate, API, worker
```

Use [athletes.py](../../backend/app/api/athletes.py) as the existing API pattern. Do not add a generic repository/service framework: handlers already use SQLAlchemy directly, with a focused shared helper only where needed.

## 3. Layer boundaries: where code belongs

| Component | Owns | Boundary to preserve |
|---|---|---|
| API handlers | Validate resource existence, orchestrate operation, return status/schema | Do not run minutes of inference inside the HTTP request |
| Pydantic schemas | Request/response shape and field validation | A schema is not a database table or a concurrency guarantee |
| SQLAlchemy models/migrations | Persistent relationships and DB constraints | Schema changes need migrations, not just new Python attributes |
| Idempotency helpers | Create-or-return behavior under uniqueness races | Database constraint is authoritative; check-then-insert alone is insufficient |
| Job state policy | Legal transitions, attempts, retry decisions | Keep pure policy separate from queue transport |
| Queue adapter | Dispatch job IDs and delayed retries | Queue contents are not the authoritative analysis status |
| Worker task | Claim, execute, atomically save/fail an attempt | Release DB transaction/lock before slow inference |
| Analyzer adapter | Call fake/real analysis and normalize results | No knowledge of HTTP requests or resource authorization |
| Storage | Stream bytes, generate keys, resolve/delete local objects | Never accept arbitrary client filesystem paths |
| Streamlit | Review interactions and presentation | UI rerenders must not create duplicate work |

The existing helper contracts explicitly commit new video/job rows. Do not assume the request's session dependency commits automatically: get_db closes sessions, while handlers/helpers currently own commit/rollback.

## 4. Domain model and storage ownership

```text
Athlete
  └── TrainingSession
        └── Video
              └── AnalysisJob (version and attempt lifecycle)
                    └── Pitch (window within that analysis)
                          └── Event (name, frame, time, method, confidence field)
```

Only Athlete is implemented today. The remaining chain is specified in [pipeline.py](../../backend/app/models/pipeline.py).

- A session groups a recording occasion; a video belongs to a session.
- The same video can have many jobs over time, including analyses under different detector versions.
- Pitches belong to a job, so a new analysis can change windows without overwriting earlier results.
- Events belong to a pitch. Planned corrections should overlay original events, not erase them.
- PostgreSQL stores metadata and relationships; LocalStorage stores uploaded bytes. Do not put video blobs into Redis.

Required exercise invariants include unique (session_id, sha256), unique storage_key, at most one queued/running job per (video_id, detector_version), and unique (job_id, window_index). These constraints are specified but not yet created by migration 0002.

Deletion is not automatically cascade-safe throughout the chain. The specification explicitly cascades Job→Pitch and Pitch→Event; inspect other foreign keys and file retention before adding deletion behavior.

## 5. Trace one upload and analysis

This is the intended exercise behavior. Athlete creation is implemented; the other HTTP endpoints listed below currently return 501. The worker task and idempotency helpers are also exercise stubs.

| Step | Request / execution | Intended outcome |
|---|---|---|
| 1 | POST /athletes | Create pseudonymous athlete; worked example exists |
| 2 | POST /athletes/{id}/sessions | Create recording session |
| 3 | POST /sessions/{id}/videos | Stream file, hash it, insert/reuse metadata; 201 new, 200 duplicate |
| 4 | POST /videos/{id}/analyze | Create committed queued job, then enqueue; 202 new, 200 existing |
| 5 | RQ calls run_analysis_job(job_id) | Claim queued job, run analyzer, save results or retry/fail |
| 6 | GET /jobs/{id} | Client polls durable job status |
| 7 | GET /videos/{id}/results?detector_version=… | Read most recent successful matching-version result |

Uploading a video and requesting analysis are separate operations. Requesting analysis returns a job acknowledgement, not a completed analysis. The worker opens its own database session; it must never reuse the API request's session.

The upload stream hashes in bounded chunks, writes a temporary file, then renames it. If the metadata deduplication helper finds an existing video, the caller deletes the redundant newly stored file. File persistence and database commit are separate operations; cleanup is part of correctness.

Current Idempotency-Key specification rejects reuse for a different video; it does not specify rejection for the same video with a different detector version. Verify and resolve that edge case in the version-consistency task before claiming full version-safe idempotency. Do not silently change the exercise contract.

## 6. Worker transactions and recovery

The [worker task specification](../../backend/worker/tasks.py) defines three boundaries:

1. **Claim transaction:** lock the queued job, transition to running, record worker identity, commit. Missing/nonqueued messages do nothing.
2. **Slow work outside a transaction:** read the stored video and call Analyzer.analyze. No long-held row lock.
3. **Result transaction:** insert all pitches/events and mark success together. On failure, roll back partial work, record retry/terminal policy, commit, then enqueue any retry.

Redis delivery and PostgreSQL commit are not one atomic transaction. The planned reliability tasks therefore add reconciliation after failed enqueue, attempt-identity checks against late stale workers, and consistent job deadlines. The basic exercise specification alone is not proof these cases are solved.

worker/run.py starts the RQ scheduler and a periodic reaper thread (default interval 60 seconds). Reaper logic and state transitions remain unimplemented. Queue jobs currently use job_timeout=-1; the reaper config defaults to 900 seconds, while each real-analyzer subprocess allows 1800 seconds. This is a recorded design gap, not a validated timeout policy.

## 7. Analyzer and artifact boundary

Analyzer has version and analyze(video_path, throwing_hand) returning AnalysisOutput: video metadata, pitch windows, event results and environment.

- FakeAnalyzer returns deterministic example events and supports a forced failure marker. It helps test backend orchestration; it says nothing about vision accuracy.
- RealAnalyzer runs auto_detect_pitch_windows.py, then analyze_pitch_timing.py for each window, and parses JSON results.
- RealAnalyzer currently removes its TemporaryDirectory when it returns. Plots, CSVs and overlays there do not become durable backend artifacts.
- The adapter currently returns width/height as None and does not map report confidence into event confidence. Do not fill gaps with invented certainty or metadata.

M6 adds durable attempt-scoped artifacts and a result manifest. Artifact and correction endpoints are proposals, not routes already registered in main.py.

## 8. Runtime and deployment shape

[Compose](../../backend/docker-compose.yml) defines Postgres, Redis, a one-off migration container, API and worker containers. API and workers share the storage volume; Postgres has its own persistent volume. Migrations complete before API/workers start. Redis currently has no declared persistent volume; recovery design cannot assume queue persistence.

Fake analysis is the default. Real analysis additionally needs analyzer dependencies in the worker image. Docker/Linux results must not be assumed identical to Mac research outputs.

The intended release is local, but current port mappings publish 8000, 5432 and 6379 without explicit loopback host binds. Authentication/resource authorization is not implemented. Check network exposure before starting this as a shared service. More worker replicas still share database, queue and storage bottlenecks.

## 9. Tests and debugging map

| Symptom / question | Read first |
|---|---|
| Request rejected or wrong status | schemas.py → api handler → errors.py |
| Duplicate uploads/jobs | services/idempotency.py → DB constraints/migration → race tests |
| Job remains queued | commit/enqueue boundary → queue.py → worker availability → reconciliation |
| Job remains running | worker task → attempt/deadline state → reaper |
| Successful job, missing video/plot | analyzer temp lifecycle → storage manifest; persistence not yet built |
| Wrong historical results | results query → job detector version → actual executed analyzer version |
| Good fake throughput, slow real video | distinguish queue wait from analyzer runtime and hardware |

logging.py supplies JSON logs and request IDs; queue metadata and worker wrapper propagate request IDs. Full attempt correlation and operational metrics still need implementation and verification.

Backend fixtures create/clear real PostgreSQL schemas and flush a Redis database. Use explicitly disposable services only. CI's required job currently excludes exercise tests; a green infrastructure job cannot prove the full pipeline works.

## 10. Instructions for the executing agent

Before the first backend task, give Ziyu a short explanation of the path in section 5 and identify which parts are implemented. Before each change, name the layer owning it, the invariant being protected, and the test or failure scenario that proves it.

Follow the [backend capability rubric](04-backend-capability-rubric.md). Ask Ziyu to predict a failure, demonstrate it, then explain the result; do not supply an answer and mark it defended. Preserve [exercise ownership](../backend_ownership.md).

Use this document for orientation, existing source/docstrings for current interfaces, active task for authorized scope, and protocols for scientific definitions. Update the map when actual architecture changes. Reading this guide does not complete the baseline task or any implementation milestone.
