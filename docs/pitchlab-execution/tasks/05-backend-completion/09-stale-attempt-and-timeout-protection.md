# 05.09 — Protect attempts and deadlines

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 05.08.

## Scope to inspect
Repository-relative targets: backend/worker/tasks.py; jobs/reaper.py; config.py; analyzers.py; concurrency tests.


## Required outcome / system gate
Paused A, reclaimed job, started B, returned A: A cannot overwrite B; total deadline and reaper grace are consistent.

## Capability gate
Explain fencing with attempt identity and distinguish timeout from cancellation.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
