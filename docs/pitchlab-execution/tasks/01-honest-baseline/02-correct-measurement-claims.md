# 01.02 — Correct measurement claims

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 01.01.

## Scope to inspect
Repository-relative targets: app.py; analyze_pitch_timing.py; generate_research_report.py; summarize_pitch_reports.py; tests/test_report_claims.py.


## Required outcome / system gate
Historical and new UI/export/overlay outputs label onset/proxies explicitly and never conclude correct or faulty anatomical sequencing; old numeric keys remain readable.

## Capability gate
Explain why a 2D curve does not validate anatomical rotation.

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
