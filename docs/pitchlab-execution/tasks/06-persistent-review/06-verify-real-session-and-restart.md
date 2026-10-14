# 06.06 — Verify real session persistence

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 06.05.

## Scope to inspect
Repository-relative targets: backend/tests/test_real_pipeline.py; private permitted clip; restart procedure.


## Required outcome / system gate
Real analysis and correction survive restart; malformed input/no pitches/analyzer failure produce usable outcomes.

## Capability gate
Demonstrate end-to-end failure diagnosis.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).

Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
