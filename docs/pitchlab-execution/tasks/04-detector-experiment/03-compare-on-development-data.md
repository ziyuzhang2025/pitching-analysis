# 04.03 — Compare on development data

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 04.02.

## Scope to inspect
Repository-relative targets: Versioned experiment outputs; development evaluator.


## Required outcome / system gate
Matched comparison retains all outcomes and applies frozen criteria without held-out tuning.

## Capability gate
Explain improvement, regression and uncertainty separately.

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
