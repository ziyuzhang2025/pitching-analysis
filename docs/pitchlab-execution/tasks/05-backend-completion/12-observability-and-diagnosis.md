# 05.12 — Trace requests and jobs

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 05.11.

## Scope to inspect
Repository-relative targets: backend/app/logging.py; API middleware; queue/worker/reaper; logging tests.


## Required outcome / system gate
Request/job/attempt identifiers correlate logs; queue wait/runtime/retries/failures observable; private paths/secrets excluded.

## Capability gate
Diagnose an injected failure from logs/state without a supplied explanation.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
