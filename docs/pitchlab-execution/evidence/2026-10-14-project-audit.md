# Project audit — 2026-10-14

Revision inspected: `dc449a1807787a023e9590fa643351f3b2a528dd` with untracked planning/visualization files. This report distinguishes code that exists from behavior that has run successfully.

## Executive result

The project is ready to begin a credible backend SWE learning track. The full track is specified in the [backend execution contract](../06-backend-execution-contract.md). It is not yet a working end-to-end backend and must not be presented as one.

The strongest existing assets are the architecture boundary, worked athlete example, real PostgreSQL/Redis test harness, explicit exercise contracts, concurrency/failure tests, Docker/CI/load-test scaffolding and contribution ownership log. The largest gap is straightforward: the five pipeline models and migration, state policy, core API endpoints, idempotency helpers, worker task, reaper and results/backfill remain exercises.

## What exists today

```text
Existing local product path
Streamlit → detector subprocesses → local output files

Intended backend path
Client → FastAPI → PostgreSQL + file storage → Redis/RQ → worker → analyzer
                    ↑                                  │
                    └──────── persisted results ───────┘
```

The backend is one application with separate API and worker processes. PostgreSQL is intended to be authoritative; Redis carries job IDs; local storage owns video bytes. FakeAnalyzer is the correct first integration target because it isolates backend behavior from computer-vision accuracy.

## Backend SWE evidence assessment

| Area | Current evidence | Status |
|---|---|---|
| Architecture | Clear API/database/queue/worker/storage boundaries and documented data flow | Scaffolded |
| API engineering | Athlete, health and version worked examples; core routes registered but return 501 | Partial |
| Relational modeling | Detailed model/migration contract and destructive PostgreSQL tests | Not implemented |
| Concurrency/idempotency | Partial unique-index and simultaneous-request tests exist | Not implemented |
| Background jobs | RQ runner, scheduler and reaper loop exist; task/state/reaper logic missing | Partial |
| Reliability | Retry, crash, late-attempt and enqueue-reconciliation tasks are specified | Not implemented |
| Testing | Root research suite passed; backend suite requires unavailable disposable services | Partially verified |
| CI | Required lint/type/non-exercise job plus informational exercise job | Scaffolded; core completion not required |
| Observability | JSON request IDs and propagation plumbing exist | Partial; full attempt/metrics proof missing |
| Security/operations | Risks and acceptance tasks documented | Not demonstrated |
| Ownership | Agent-written scaffold and Ziyu-owned exercises are explicitly separated | Strong foundation |

This can become strong internship/junior-backend evidence only when implementation, failure demonstrations and Ziyu's independent explanation are all recorded. Generated code or passing tests alone do not establish ownership.

## Checks performed

- Root suite: 20 passed in 9.23 seconds using pytest from an isolated temporary location.
- Root environment: Python 3.12.13, MediaPipe 0.10.21, OpenCV 4.11.0.86, NumPy 1.26.4 and Pandas 3.0.3.
- Docker daemon: unavailable; backend integration/exercise tests not run.
- Backend source: exercise stubs confirmed across models, state, endpoints, idempotency, worker and reaper.
- CI: the required job excludes `ziyu` exercise tests; the exercise job is informational.
- Historical detector output: selected set hashed, but source-video and generation provenance are missing.
- Instruction navigation: all local Markdown links resolve and exactly one task is READY.

Graphify produced a 233-node documentation graph with 241 edges and 26 communities; the graph health diagnostic reported no dangling, missing, collapsed or self-loop edges. Its installed code parsers lacked Python/JSON/Bash grammars, so it contains zero AST code nodes and must not be treated as a complete code graph.

## Risks to keep visible

1. Backend test fixtures drop the configured PostgreSQL `public` schema and flush Redis DB 15. Never point them at valued services.
2. A green required CI job does not prove the seven exercises work.
3. Compose currently publishes API, PostgreSQL and Redis ports without explicit loopback binds; the release is only intended for local use.
4. Queue delivery and database commit are not atomic; reconciliation remains planned work.
5. Historical output files do not establish detector reproducibility or unseen-athlete accuracy.
6. RealAnalyzer temporary artifacts are not durable backend artifacts.

## Immediate next task

Open [05.01 — models and migration](../tasks/05-backend-completion/01-models-and-migration.md). Ziyu implements only the five models, exports and migration 0002. Before running tests, start explicitly disposable PostgreSQL/Redis. The task is complete only after the exercise test, migration round trip, non-exercise regression suite, lint/type checks and capability explanation are separately recorded.

Do not start sessions/uploads or the worker task until 05.01 passes both gates.
