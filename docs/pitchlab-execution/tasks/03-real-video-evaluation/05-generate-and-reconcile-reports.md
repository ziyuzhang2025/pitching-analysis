# 03.05 — Generate and reconcile reports

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 03.04.

## Scope to inspect
Repository-relative targets: research/obp_summary.py; research/rq1_summary.py; research/results/RQ2_FINDINGS.md.


## Required outcome / system gate
One documented command generates report from results; RQ2 48.8/49.8 discrepancy resolved with named column/filter; missing BR included in coverage.

## Capability gate
Trace a published number to its exact rows.

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
