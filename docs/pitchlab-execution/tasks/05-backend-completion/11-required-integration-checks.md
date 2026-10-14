# 05.11 — Require full backend checks

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 05.10.

## Scope to inspect
Repository-relative targets: backend tests; .github/workflows/backend.yml; pyproject.toml.


## Required outcome / system gate
Disposable backend suite passes; progress 7/7; exercise failures block CI; lint/types include relevant worker code.

## Capability gate
Write an invariant test beyond the supplied exercise tests.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
