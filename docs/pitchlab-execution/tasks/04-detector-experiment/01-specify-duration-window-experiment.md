# 04.01 — Specify duration-window experiment

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: M3 development evidence.

## Scope to inspect
Repository-relative targets: Experiment protocol; detector callers inventory.


## Required outcome / system gate
Duration choices, rounding, baseline, promotion rule and held-out procedure frozen before tuning.

## Capability gate
State a result that would reject the proposed change.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [detector-experiments](../../protocols/detector-experiments.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
