# 05.07 — Implement versioned results and backfill

Status: OUTLINE — refine before execution.
Owner: Ziyu implements; agent coaches/reviews under existing exercise ownership rules.
Dependencies: 05.06.

## Scope to inspect
Repository-relative targets: backend/app/api/results.py; admin.py; tests/exercises/test_ex7_results_and_backfill.py.
Read [exercise specification](../../../backend_exercises.md) and target docstrings; preserve their interfaces.

## Required outcome / system gate
Explicit version and latest-successful selection work; relationship loading avoids N+1.

## Capability gate
Explain historical consistency while a backfill runs.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
