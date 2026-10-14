# 03.03 — Evaluate baselines and agreement

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 03.02.

## Scope to inspect
Repository-relative targets: evaluate_pitch_accuracy.py; research/rq1_summary.py; tests/test_rq1_summary.py.


## Required outcome / system gate
Frozen baseline comparison, coverage, errors, interval errors and annotator agreement computed; failed predictions retained.

## Capability gate
Recalculate a small fixture by hand and explain denominators.

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
