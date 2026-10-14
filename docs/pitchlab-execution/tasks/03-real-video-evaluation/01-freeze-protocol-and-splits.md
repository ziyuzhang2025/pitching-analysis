# 03.01 — Freeze evaluation protocol and splits

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: M2.

## Scope to inspect
Repository-relative targets: labels/splits.json; pitch_labels.py; tests/test_rq1_summary.py.


## Required outcome / system gate
Athlete grouping, metrics and denominators frozen before held-out access; leakage checker rejects cross-split derivatives.

## Capability gate
Explain independence of athlete versus frame.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [dataset-splits](../../protocols/dataset-splits.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
