# Verified current state

Snapshot refreshed: 2026-10-14; inspected source revision dc449a1. These are observations, not permanent guarantees. Recheck HEAD and working changes at task start.

| Classification | Observation | Source / evidence |
|---|---|---|
| Verified execution | Root research suite: 20 passed, no skips, 9.23 s; pytest loaded from isolated temporary target | [Verification log](evidence/verification-log.md) |
| Verified inspection | Core backend model/worker/API/reaper code remains exercises/stubs | backend/app/models/pipeline.py; backend/worker/tasks.py; backend/app/api/ |
| Verified inspection | Required backend CI excludes exercise tests; exercise job permits failure | .github/workflows/backend.yml |
| Verified local data | 10 v2 pitches, athlete P01, all dev, annotation key A1_anchored | labels/pitch_labels_v2.json; do not copy private records here |
| Verified inspection | Coach sequence conclusions conflict with research limitations | app.py:build_pitch_report; research/results/RQ2_FINDINGS.md |
| Verified inspection | Pelvis "peak" detector actually returns onset | tests/test_signals.py |
| Verified inspection | RealAnalyzer temp artifacts disappear after return; confidence is not mapped | backend/app/analyzers.py |
| Verified recomputation | Raw saved simulation: 19,296 rows, 402 pitches, 100 athletes | CSVs referenced in research/results/rq2_summary.json |
| Verified recomputation | Side/240 fps FFS median absolute error 16.1 ms (402 values), BR 15.5 ms (401 values) | Same saved rows; not a fresh simulation |
| Open discrepancy | Raw order_ok_peakvel is 49.8%; prose says 48.8% | Reconcile oracle/end-to-end column and filters |
| Verified environment limitation | Root `.venv` contains MediaPipe 0.10.21, OpenCV 4.11.0.86, NumPy 1.26.4 and Pandas 3.0.3, but not pytest | Temporary pytest install used only for root suite |
| Verified environment limitation | Docker client exists; daemon unavailable on 2026-10-14 | Backend integration/exercise tests not run; fixtures are destructive to their configured test schema/Redis DB |
| Verified artifact state | A historical five-window output set was hashed, but its source video and generation command cannot be established from the saved files | [Baseline manifest](evidence/baseline-manifest.md) |
| Tooling limitation | Graphify detected 170 files, but its installed AST parser lacked Python/JSON/Bash grammars | Direct inspection used; zero code AST nodes is not a clean architecture result |

## Proposed, not verified

- Five-athlete, two-session, 100-pitch feasibility target.
- 102–152 hours for the earlier core plan; added backend operations tasks require extra capacity.
- New physical-duration detector windows and promotion tolerances.
- A functional integrated app after planned tasks.

## Unknown / not demonstrated

Held-out real-video accuracy; independent human agreement; full backend behavior; fresh backend dependency installation; current remote CI; end-to-end video workflow; real runtime and scaling; backup restoration; network access controls.

Earlier conversational descriptions overstated backend readiness. Use inspected implementation, not those descriptions.
