# Backend SWE capability rubric

Target: credible internship/junior backend evidence. No claim of seniority follows from completing this project.

Assess each row separately: NOT DEMONSTRATED → IMPLEMENTED → VERIFIED → DEFENDED. Record dates and evidence in milestone acceptance. Assistance is allowed and attributed; defense is Ziyu's own reasoning.

| Capability | Required system proof | Independent demonstration |
|---|---|---|
| Relational modeling | FK/CHECK/unique constraints; safe disposable migration round trip | Explain why application checks alone cannot enforce concurrency invariants |
| SQL and API design | Bounded pagination, stable ordering, documented errors, query-count check, representative EXPLAIN | Choose an index based on a query and explain its write cost |
| Concurrency | Concurrent submissions yield one active job; duplicate delivery harmless | Reproduce a race and explain locking/transaction boundaries |
| Job reliability | Failed enqueue reconciled; stale attempt cannot overwrite winner; timeout bounded | Diagnose one injected failure from logs and database state |
| Version/provenance | Executed version matches result metadata; historical results selectable | Explain behavior when a release changes while jobs wait |
| Testing | Meaningful failure tests plus real DB/queue integration | Write one new test from an invariant, and explain a test suite blind spot |
| Observability | Request/job/attempt correlation; queue wait/runtime/retry/failure signals | Trace one failed analysis through API, queue and worker |
| Performance | Repeated bounded workload, query inspection, one measured bottleneck decision | Distinguish API latency, queue latency and analyzer runtime |
| Security | Verified local exposure, upload/path controls, sanitized errors/logs; authorization before sharing | Explain trust boundaries and attempt an invalid resource/path access |
| Operations | Clean start, graceful stop, recovery, disposable backup/restore and release procedure | Restore a sample session and explain schema rollback limitations |
| Judgment/ownership | ADRs, attributed work, justified scope cuts | Compare two realistic alternatives using project constraints |

## Assessment rules

A passing test is not proof of personal understanding. A spoken answer is not proof the implementation works. Require both gates; an agent must never fabricate or pre-complete the defense.

For defense, ask Ziyu to predict behavior, run the failure scenario, reconcile the observation with the prediction, and explain one alternative. Record observed gaps, then schedule targeted practice.

For a local release, authenticated multi-user operation is explicitly NOT DEMONSTRATED. A shared deployment cannot pass on the strength of local-only checks.
