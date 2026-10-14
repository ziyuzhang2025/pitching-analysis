# 05.06 — Implement crash recovery

Status: OUTLINE — refine before execution.
Owner: Ziyu implements; agent coaches/reviews under existing exercise ownership rules.
Dependencies: 05.05.

## Scope to inspect
Repository-relative targets: backend/app/jobs/reaper.py; worker/run.py; tests/exercises/test_ex6_reaper.py.
Read [exercise specification](../../../backend_exercises.md) and target docstrings; preserve their interfaces.

## Required outcome / system gate
Timed-out work retries or terminates; concurrent reapers do not claim the same row unsafely.

## Capability gate
Distinguish slow worker from dead worker and identify stale-write risk.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
