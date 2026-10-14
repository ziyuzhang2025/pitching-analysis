# 01.01 — Record the actual baseline

Status: BLOCKED. Inspection recorded 2026-10-14; selected historical outputs lack source-video provenance and the capability review is pending.
Dependency: none. Scope: documentation and isolated diagnostic checks only.

## Purpose and evidence

Establish what exists before making changes. Prior checks are summarized in [current state](../../02-current-state.md), but must not be treated as live guarantees.

First read [backend architecture](../../05-backend-architecture.md). Explain the current local UI path and intended API/worker path before recording the baseline; this orientation does not replace inspection.

## Execution steps

1. Run `git status --short` and `git rev-parse HEAD` from the repo root. Record dirty paths without changing them.
2. Inspect root requirements, existing virtual environment, detector version and test imports. Record Python/platform and installed dependency versions without dumping environment secrets.
3. Run `.venv/bin/python -m pytest tests -q -rs -p no:cacheprovider` if that environment has pytest. If unavailable, use an isolated temporary test dependency location or report the setup blocker. Do not replace the existing MediaPipe stack just to run tests.
4. Capture pass/fail/skip counts. If analyzer imports cause tests to skip, do not report full coverage. Record failures without fixing unrelated code.
5. Inspect core backend model, state, worker and endpoint stubs; record which remain unfinished. Inspect CI exercise inclusion.
6. Check Docker availability read-only. Do not start destructive fixtures against existing services. Backend execution is not required to finish this baseline task if explicitly marked unverified.
7. Select an existing local session and output set, inspect the recorded input/configuration identity, and compute SHA-256 hashes. Do not invent missing provenance. If no usable private fixture exists, record this and leave reproducibility verification blocked.
8. Populate [baseline manifest](../../evidence/baseline-manifest.md), append [verification log](../../evidence/verification-log.md), update current state and [handoff](../../progress/handoff.md).
9. Record Ziyu's explanation of the boundary between passing helper tests, saved simulation evidence and validated real-video behavior. Capability gate can remain pending.
10. Mark this task system-complete only when the checklist below is satisfied; nominate 01.02 for refinement. Do not implement 01.02 automatically.

## Success criteria

- [ ] Exact source revision and dirty state recorded.
- [ ] Test outcomes actually observed, including skips or setup blockers.
- [ ] Backend stubs versus working infrastructure accurately distinguished.
- [ ] Selected artifacts/input have recorded hashes, or missing-fixture dependency is explicit and task remains blocked where needed.
- [ ] Unknown provenance and unexecuted checks remain labeled unknown.
- [ ] No participant media, credentials or private path mapping committed.
- [ ] Ziyu can explain why these checks do not establish unseen-athlete accuracy (capability gate).

No code edits, version bump, threshold tuning or database reset belongs to this task.
