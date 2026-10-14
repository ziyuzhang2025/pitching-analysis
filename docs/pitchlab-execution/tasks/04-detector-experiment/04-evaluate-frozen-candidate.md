# 04.04 — Evaluate frozen candidate

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 04.03.

## Scope to inspect
Repository-relative targets: Frozen config; evaluation log and report.


## Required outcome / system gate
One logged held-out comparison yields accept/reject/restrict decision; no repeated tuning on that set.

## Capability gate
Defend a negative result and next valid experiment.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [evaluation](../../protocols/evaluation.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
