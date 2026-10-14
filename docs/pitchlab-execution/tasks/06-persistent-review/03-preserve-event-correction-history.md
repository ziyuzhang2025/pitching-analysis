# 06.03 — Preserve correction history

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 06.02.

## Scope to inspect
Repository-relative targets: Correction table/migration; backend/app/api/corrections.py; tests.


## Required outcome / system gate
Append-only corrections validate event/frame; automatic result unchanged; repeated edits survive restart.

## Capability gate
Explain distinction between correction provenance and independent ground truth.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [annotation](../../protocols/annotation.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
