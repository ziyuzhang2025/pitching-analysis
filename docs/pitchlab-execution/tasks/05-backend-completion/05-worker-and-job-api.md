# 05.05 — Implement worker and job API

Status: OUTLINE — refine before execution.
Owner: Ziyu implements; agent coaches/reviews under existing exercise ownership rules.
Dependencies: 05.04.

## Scope to inspect
Repository-relative targets: backend/worker/tasks.py; backend/app/api/jobs.py; tests/exercises/test_ex5_worker_and_jobs.py.
Read [exercise specification](../../../backend_exercises.md) and target docstrings; preserve their interfaces.

## Required outcome / system gate
Claim/work/commit boundaries and atomic result writes pass; duplicate delivery is harmless.

## Capability gate
Explain why inference cannot hold a long DB transaction.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
