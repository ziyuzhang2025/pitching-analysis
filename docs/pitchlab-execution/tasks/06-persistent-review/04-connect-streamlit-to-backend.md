# 06.04 — Connect Streamlit workflow

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 06.03.

## Scope to inspect
Repository-relative targets: app.py; small API client boundary; UI/integration checks.


## Required outcome / system gate
Session/upload/poll/review/save/export works; rerenders do not resubmit; explicit local mode during migration.

## Capability gate
Trace one UI action through persistence and failure handling.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
