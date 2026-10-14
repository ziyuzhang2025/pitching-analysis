# 05.15 — Rehearse operations

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 05.14.

## Scope to inspect
Repository-relative targets: backend worker startup/shutdown; migrations; operations runbook; disposable recovery checks.


## Required outcome / system gate
Graceful stop/restart demonstrated; disposable DB plus artifacts backup restores consistent sample results; migration/release recovery documented.

## Capability gate
Restore a sample session and explain why destructive downgrade is not a safe universal rollback.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
