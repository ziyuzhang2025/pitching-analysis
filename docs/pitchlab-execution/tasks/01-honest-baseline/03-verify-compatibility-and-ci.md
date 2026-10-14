# 01.03 — Verify compatibility and CI

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 01.02.

## Scope to inspect
Repository-relative targets: tests/; .github/workflows/; docs/verification.md.


## Required outcome / system gate
Root suite and legacy fixtures pass; relevant source changes trigger root tests; no detector threshold changed inadvertently.

## Capability gate
Explain a regression the new tests would catch.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [measurement-contract](../../protocols/measurement-contract.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
