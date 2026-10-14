# 06.01 — Persist artifacts and manifest

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: M4 decision + M5.

## Scope to inspect
Repository-relative targets: backend/app/analyzers.py; storage.py; pipeline models; new migration; persistence tests.


## Required outcome / system gate
Artifacts survive temporary-directory exit; manifest records input/config/source/version/env; only winning attempt publishes; orphan cleanup defined.

## Capability gate
Explain file persistence versus DB transaction boundary.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
