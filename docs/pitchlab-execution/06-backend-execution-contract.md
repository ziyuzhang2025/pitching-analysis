# Backend execution contract

Status: AUTHORITATIVE PLAN. Updated 2026-10-14. This file fixes the order, boundaries and evidence required for the complete backend track. Individual task files own the active implementation checklist.

## Definition of backend completion

Backend completion means a client can create an athlete/session, stream and deduplicate a video, request deterministic fake analysis, observe a durable job lifecycle, retrieve versioned persisted results, survive duplicate delivery and defined failures, and recover after restart. It also requires bounded APIs, correlated diagnostics, verified local exposure and a rehearsed disposable restore.

It does not mean the real detector is accurate, the Streamlit UI is integrated, or the service is safe for shared deployment.

## Rules for every task

1. Only [the active task](tasks/active.md) is authorized. A later task stays OUTLINE until its dependency evidence is recorded and its exact source interfaces are re-inspected.
2. Ziyu owns Exercises 1–7. Agents explain, review and run checks unless a specific exercise is explicitly delegated and attributed.
3. Begin with a failing test or injected failure. State the owning layer, invariant and expected observation before editing.
4. Use disposable PostgreSQL and Redis only. The test fixtures drop the configured `public` schema and flush Redis DB 15.
5. Finish with the task test, non-exercise regression tests, Ruff, mypy, diff review, verification log and separate system/capability gate results.
6. FakeAnalyzer proves orchestration only. RealAnalyzer accuracy and runtime claims require later research evidence.

## Complete task sequence

| Task | Change boundary | Required invariant / failure proof | Minimum verification | Capability proof |
|---|---|---|---|---|
| [05.01](tasks/05-backend-completion/01-models-and-migration.md) | Five models, exports, migration 0002 | DB rejects invalid/duplicate state; active-job partial uniqueness; cascades; reversible migration | Exercise 1; upgrade/downgrade/upgrade; non-exercise suite; Ruff; mypy | Explain why DB constraints beat check-then-insert |
| [05.02](tasks/05-backend-completion/02-state-machine-and-retries.md) | `app/jobs/state.py` only | Illegal/terminal transitions rejected; retry delay stays within exponential full-jitter cap | Exercise 2 plus deterministic boundary tests using patched randomness | Predict retry distribution for simultaneous failures |
| [05.03](tasks/05-backend-completion/03-sessions-and-streamed-uploads.md) | Session routes and upload/get route | Missing parent 404; bounded streaming; MIME/size validation; failed/deduplicated writes leave no orphan file | Exercise 3; large/empty/unsupported upload cases; storage cleanup assertion | Explain memory bound and file/DB atomicity gap |
| [05.04](tasks/05-backend-completion/04-idempotency-and-concurrent-requests.md) | Idempotency helpers and analyze route | Eight concurrent identical requests yield one identity/active job; commit precedes enqueue; key misuse rejected per contract | Exercise 4 race tests and Redis-down injection | Walk two concurrent requests through the uniqueness race |
| [05.05](tasks/05-backend-completion/05-worker-and-job-api.md) | Worker task and job handlers | Claim commits before inference; results/status commit atomically; duplicate delivery is harmless; partial results roll back | Exercise 5; fake success/failure/duplicate delivery; query persisted results | Draw the three transaction boundaries |
| [05.06](tasks/05-backend-completion/06-crash-recovery.md) | Reaper policy called by existing runner | Only stale running jobs are locked/retried/failed; concurrent reapers skip claimed rows | Exercise 6 plus two-reaper scenario | Distinguish slow, dead and late workers |
| [05.07](tasks/05-backend-completion/07-versioned-results-and-backfill.md) | Results and admin routes | Explicit version selects matching success; default is latest successful; backfill excludes existing active/successful version; no N+1 | Exercise 7; query-count assertion; bounded backfill sample | Explain consistent reads during version rollout |
| [05.08](tasks/05-backend-completion/08-undelivered-job-reconciliation.md) | Queue/reconciliation service and runner wiring | A committed queued job lost before Redis enqueue is eventually submitted; repeated reconciliation remains duplicate-safe | Inject enqueue failure, reconcile twice, execute once | Explain DB/Redis dual-write limitation |
| [05.09](tasks/05-backend-completion/09-stale-attempt-and-timeout-protection.md) | Job attempt identity, worker/reaper deadline policy | Reclaimed attempt B cannot be overwritten by late attempt A; configured analyzer deadline fits reaper grace | Paused-A/reclaim-B/release-A concurrency test; timeout integration check | Explain fencing and why timeout is not cancellation |
| [05.10](tasks/05-backend-completion/10-detector-version-consistency.md) | Analyzer/worker version enforcement | Executed analyzer version equals persisted job/result version; mismatch cannot succeed under a false label | Queue old version, switch configured analyzer, observe explicit safe outcome | Choose and defend drain/fail/version-routed behavior |
| [05.11](tasks/05-backend-completion/11-required-integration-checks.md) | Test configuration and backend CI | All seven exercises become required; worker code is linted/typed; one new invariant test catches an unsupplied failure | Full disposable suite; `progress.py` 7/7; coverage ≥80%; required CI config inspection | Write and defend one original test |
| [05.12](tasks/05-backend-completion/12-observability-and-diagnosis.md) | Structured logging and minimal metrics | Request/job/attempt correlation across API/queue/worker/reaper; queue wait/runtime/retry/failure visible; no secret/private path leakage | Capture one successful and one failed trace; log-schema tests | Diagnose injected failure without provided answer |
| [05.13](tasks/05-backend-completion/13-sql-pagination-and-api-contract.md) | Pagination/resource queries/error contract | Stable bounded ordering under equal timestamps; no duplicate/omitted pages; bounded query count; consistent error shape | Boundary pagination tests, query count, representative `EXPLAIN (ANALYZE, BUFFERS)` | Justify an index and its write cost |
| [05.14](tasks/05-backend-completion/14-security-and-exposure-review.md) | Compose binds, upload/storage/error boundaries | Local services bind as intended; path traversal/oversize/empty/malformed access rejected; errors/logs sanitized | Socket/bind inspection and adversarial API/storage tests | Identify every trust boundary and shared-deployment blocker |
| [05.15](tasks/05-backend-completion/15-shutdown-migrations-and-restore.md) | Shutdown/release/backup runbook and necessary wiring | In-flight behavior is documented on stop; restart recovers durable state; DB plus stored objects restore consistently | Clean start/stop/restart; backup/restore into fresh disposable environment; release rehearsal | Restore a sample and explain why downgrade is not universal rollback |

## Milestone M5 acceptance

M5 passes the system gate only when:

- all task system gates above link to observed evidence;
- one upload → analyze → worker → persisted fake result → results read succeeds after restart;
- concurrent duplicate submissions create one active job;
- enqueue loss, analyzer failure, worker loss and late stale completion have demonstrated outcomes;
- required CI fails when an exercise regression is introduced;
- actual local bind addresses, restore procedure and known shared-deployment blockers are recorded.

M5 passes the capability gate only when Ziyu independently predicts, demonstrates and explains one database race, one queue/worker failure, one SQL/index decision and one restore limitation. Agents must record gaps rather than supplying answers and marking them defended.

After M5, return to the research milestones before claiming real-video correctness or completing the persistent review application.
