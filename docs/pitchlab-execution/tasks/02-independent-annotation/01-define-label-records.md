# 02.01 — Define label records

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: M1.

## Scope to inspect
Repository-relative targets: pitch_labels.py; tests/test_labels.py; tests/test_annotation_records.py.


## Required outcome / system gate
Additive metadata distinguishes session/camera/pass and labeled/unlabelable/not_attempted; v1/v2 compatibility remains tested.

## Capability gate
Explain identity and missing-event semantics.

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
