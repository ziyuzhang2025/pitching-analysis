# 05.08 — Recover undelivered jobs

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 05.07.

## Scope to inspect
Repository-relative targets: backend/app/queue.py; worker/run.py; jobs recovery code; new reconciliation tests.


## Required outcome / system gate
DB commit then enqueue failure is injected; bounded reconciliation eventually submits it; duplicate deliveries remain harmless.

## Capability gate
Explain why a DB transaction cannot atomically commit to Redis.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
