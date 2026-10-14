# Verification log

## 2026-10-12 — Prior planning checks

Source inspected: dc449a1. Scope: root tests and saved research outputs; not backend integration.

Command from repo root:
```sh
PYTHONPATH=/private/tmp/pitchlab-plan-check.cIEL2k MPLCONFIGDIR=/private/tmp/pitchlab-plan-check.cIEL2k/mpl .venv/bin/python -m pytest tests -q -rs -p no:cacheprovider
```

Observed: 20 passed in 9.17 s, no skips. Pytest was installed in a temporary directory, without editing project dependencies. This temporary path may disappear; it is historical evidence, not the permanent setup instruction.

Saved CSV recomputation: 19,296 rows, 402 pitches, 100 athletes; side/240 fps FFS 16.1 ms over 402 values; release 15.5 ms over 401. No fresh inference or simulation run.

Docker info reported daemon unavailable. Backend suite not executed.

## New entries

Append task-specific evidence here; never turn a planned check into a passing result.

## 2026-10-12 — Instruction folder creation

Created 66 Markdown files. A recursive local-link audit checked 93 links: zero broken targets. Task-status audit found exactly one READY task; later implementation tasks remain OUTLINE. The template is also marked OUTLINE. Git inspection showed the new instruction folder as untracked; no tracked product source was changed. No application tests were rerun for this documentation-only change. This check validates navigation and task readiness markers, not software behavior or scientific protocols.

## 2026-10-13 — Backend architecture orientation

Added a source-inspected architecture guide and linked it into the reading order and first baseline task. Inspected API registration, database sessions, models, upload/storage, idempotency specifications, queue/worker entry points, analyzer adapters, logging, Compose and the Streamlit subprocess path. Distinguished implemented components from exercise stubs and planned additions.

A recursive local Markdown-link audit checked 104 links across 67 Markdown files: zero broken targets. Git status showed no tracked product-source modifications. No application or backend integration tests were run for this documentation-only update. Source inspection and link validation do not establish runtime correctness. The active task remains baseline recording; no implementation or capability milestone was completed.

## 2026-10-14 — Backend-first preflight and instruction update

Inspected revision `dc449a1807787a023e9590fa643351f3b2a528dd`. Before this update, untracked paths were `.lavish/`, `docs/pitchlab-execution/` and `docs/superpowers/`; `graphify-out/` was created by the architecture audit. No backend exercise implementation was written.

The root `.venv` uses Python 3.12.13 on macOS 26.3.1 arm64 and contains MediaPipe 0.10.21, OpenCV 4.11.0.86, NumPy 1.26.4 and Pandas 3.0.3. It did not contain pytest. Installed pytest into an isolated temporary target and ran:

```sh
PYTHONPATH="<temporary-pytest-target>:." MPLCONFIGDIR=/private/tmp/pitchlab-mpl \
  .venv/bin/python -m pytest tests -q -rs -p no:cacheprovider
```

Observed: 20 passed in 9.23 seconds. The temporary dependency location is not part of the project environment.

`docker info` could not connect to the Docker daemon. Backend tests were not run because their fixtures drop the configured test database's `public` schema and flush Redis DB 15; no disposable services were available. Direct inspection confirmed the five pipeline models/migration, state policy, session/video/job/result/admin handlers, idempotency helpers, worker task and reaper remain exercises/stubs. CI continues to exclude exercise tests from its required job and marks exercise progress informational.

Historical output prefix `outputs/ui_test_pitch_01_20260622_121032` was inspected and hashed. Representative SHA-256 values:

```text
ca214081cfe1c5fc4f52bd3634bba91223bbe3f6ce05e6a16ca748e9a7dfa0df  pitch_windows.json
a8b7e8cfae939071c946128b9d8a2f7d111670febdcdfdac376e7a734542d0d4  window_1_timing_report.json
c9e4de622965007313c1343e23355f2330055744bef19762bb45c01f5c2a7eb0  window_1_landmarks.csv
659bd73123484f4d65001fe466e47ea54b32bf0ac54fc25450b70e4c353d1a4e  window_1_pose_overlay.mp4
```

The saved report records 30 fps and 2,401 original frames. The source video, its checksum, the exact generation command and version provenance were not found, so research baseline task 01.01 remains blocked. The backend preflight is sufficient to activate Exercise 1 because its correctness uses deterministic fixtures and PostgreSQL constraints, not detector accuracy.

Graphify detected 170 files (77 code, 86 documents, 3 papers, 4 images) and no sensitive files. Its installed AST parser reported missing Python/JSON/Bash grammar dependencies and produced zero AST nodes; this limitation is retained rather than treating the graph as complete. Direct source inspection remains the basis for code-state claims.

Semantic extraction produced a documentation graph with 233 nodes, 241 edges and 26 communities. The diagnostic reported no dangling, missing, collapsed or self-loop edges. Outputs are in `graphify-out/` (`graph.html`, `GRAPH_REPORT.md`, `graph.json`). Recorded extraction usage: 48,340 input tokens and 35,740 output tokens. Because code AST extraction was unavailable, the graph is a documentation map, not complete proof of code relationships.

Final instruction audit checked 128 local links across the root README and 69 execution-guide Markdown files: zero broken targets. Exactly one task is READY: `05-backend-completion/01-models-and-migration.md`; the active-task pointer resolves to it. `git diff --check` reported no tracked whitespace errors. Root `README.md` is modified; the execution guide and graph outputs remain untracked. No commit, push, database mutation or backend exercise implementation was performed.
