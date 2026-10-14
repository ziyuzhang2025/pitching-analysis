# 04.02 — Implement duration-window candidate

Status: OUTLINE — refine before execution.
Owner: Assign when activated; record assistance and implementation ownership.
Dependencies: 04.01.

## Scope to inspect
Repository-relative targets: analyze_pitch_timing.py; auto_detect_pitch_windows.py; app.py; simulation/stress callers; backend/app/analyzers.py; tests/test_signals.py.


## Required outcome / system gate
Equivalent physical-duration signal tests across FPS; short/missing/noisy inputs checked; 1.0.0 remains reproducible.

## Capability gate
Explain differentiation noise and smoothing tradeoffs.

## Refinement and execution
- [ ] Verify dependencies and current source; inspect all affected callers.
- [ ] Specify exact interfaces, errors, compatibility and named verification assertions in this file.
- [ ] Establish the failing check or reproducible operational baseline.
- [ ] Implement/perform the bounded work under the project ownership rules.
- [ ] Run the specified checks; retain failures, missing data and limitations.
- [ ] Append evidence; update status and handoff; assess both gates separately.

Evidence destination: [verification log](../../evidence/verification-log.md).
Required protocol: [detector-experiments](../../protocols/detector-experiments.md).
Stop if a dependency is unverified, a contract conflict affects behavior, or the task requires authority beyond its scope. Do not mark complete from inspection alone.
