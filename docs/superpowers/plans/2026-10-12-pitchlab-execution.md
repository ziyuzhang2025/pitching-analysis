# Pitch Lab: validated event review implementation plan

> Execution mode: Ziyu implements the existing backend exercises; the assistant explains, reviews, and helps investigate failures. This plan is a proposed sequence, not authorization to implement it. Use the executing-plans workflow for subsequent implementation. Checkboxes are acceptance evidence, not calendar promises.

**Goal:** Deliver a local application that detects front-foot contact and approximate ball release, lets a reviewer correct them, preserves the original results, and exposes reproducible evidence about accuracy and system reliability.

**Architecture:** Retain Streamlit, the Python detector, and the existing FastAPI/PostgreSQL/Redis worker scaffold. Establish valid measurements in the local research workflow first; then connect the existing UI to the completed backend. Keep technical inspection behind an optional details view.

**Tech stack:** Existing Python, OpenCV, MediaPipe, pandas, Streamlit, FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis/RQ, pytest, Ruff, mypy, Docker and Locust. No new frontend framework or cloud service is required for this release.

**Specification basis:** User request for a verified execution plan; career roadmap sections 18–21 and 35; `docs/RESEARCH_GUIDE.md`; `docs/backend_exercises.md`. Proposed decisions below supersede conflicting old feature ambitions for this release only. Administrative university rules and external dataset licensing have not been reverified.

## 1. Evidence checked on 12 October 2026

Inspected checkout: `dc449a1`. Product source was not changed during planning.

| Finding | Evidence | Consequence |
|---|---|---|
| Research helpers and label tests pass | Executed root `tests/`: **20 passed in 9.17 s**, no skips | Useful regression baseline; does not validate actual video accuracy |
| Backend core is unfinished | `app/models/pipeline.py` contains specifications; `worker/tasks.py` raises `NotImplementedError`; core endpoints raise 501 | Earlier conversational claims of a functioning recovery pipeline were overstated |
| Backend CI can be green without the exercises passing | `.github/workflows/backend.yml` excludes `ziyu` tests in required checks; exercise job is informational | Promote exercise tests to required before declaring backend complete |
| Real-video evidence is development-only | Local `labels/pitch_labels_v2.json`: 10 pitches, one athlete P01, all dev, annotation key `A1_anchored` | No independently held-out athlete or blind reference demonstrated |
| Sequence interpretation conflicts with research findings | `app.py:build_pitch_report`, `analyze_pitch_timing.py:classify_sequence`, `research/results/RQ2_FINDINGS.md` | Correct claims before presenting the app |
| Pelvis event naming is misleading | Existing test explicitly verifies `detect_pelvis_peak` returns onset | Preserve compatibility but label it as onset/proxy |
| Artifacts disappear in backend adapter | `RealAnalyzer.analyze` uses `TemporaryDirectory` and returns events/environment, not persistent artifacts | Add durable artifacts before UI integration |
| Confidence is lost in adapter | `parse_timing_report` does not populate `EventResult.confidence` | Do not display fabricated probabilities; preserve named heuristic quality separately |
| Saved simulation is substantial and inspectable | Recounted raw CSVs: 19,296 rows, 402 pitches, 100 athletes | Reuse this study rather than start another broad experiment |
| Selected simulation values reproduce from saved rows | Side/240 fps: FFS median absolute error 16.1 ms (402 values), BR 15.5 ms (401 values), oracle 2D pelvis 26.9 ms, ideal ground-plane pelvis 2.7 ms | Explicitly disclose simulation, oracle inputs, and missing outcomes |
| One report percentage needs reconciliation | Raw `order_ok_peakvel` gives 49.8%; findings prose says 48.8% | Check intended metric/filter and regenerate prose; do not silently substitute |
| Full backend execution not verified | Docker client exists but daemon is unavailable | Integration, migration, recovery and performance claims remain pending |

Test verification used the existing research `.venv`, with pytest installed only under `/private/tmp/pitchlab-plan-check.cIEL2k`. No project dependency file was changed. This was not a new full simulation run or an end-to-end MediaPipe benchmark.

## 2. Release scope and constraints

- Primary user: a pitcher or reviewer checking visible events in a recorded session.
- Primary scientific question: how accurately and repeatably can visible foot contact and ball release be located, and where does automation fail?
- Primary supported pilot condition: original 240 fps side-view footage, full body visible. Lower frame rates remain experimental until evaluated.
- Primary output: estimated/corrected event frames and time from foot contact to release. Never infer improvement in performance from a change in this interval alone.
- Raw automatic results are immutable; corrections and independent reference annotations are separate records.
- Confidence labels are heuristic quality labels until calibrated. A study-level confidence interval is not a probability that an individual pitch is correct.
- Preserve legacy result keys and v1/v2 label reading. New names and metadata are additive, with documented legacy meaning.
- Every release identifies source revision, detector version, configuration, environment, and input identity.
- Local use only for this release. Network/public deployment requires a separate authentication and authorization task; the existing API has no demonstrated user isolation.
- Ziyu's ownership log distinguishes personally implemented, assisted, and scaffolded work.

## 3. Capacity and sequencing

Estimated focused work: **102–152 hours**, including learning/debugging but excluding participant scheduling and long compute runs. These are planning estimates, not measured task durations. At 4 hours/week this is about **26–38 working weeks**; exams and collection delays extend elapsed time. Re-estimate after each milestone.

| Stage | Hours | Dependency | Deliverable |
|---|---:|---|---|
| 1. Honest baseline | 6–8 | None | Correct claims, preserved baseline, reproducible test command |
| 2. Blind annotation | 12–18 | 1 | Independent event labels and collection protocol |
| 3. Pilot evaluation | 18–26 | 2 + available recordings | Accuracy, missingness, human agreement, failure report |
| 4. One detector experiment | 12–20 | 3 development evidence | Accept/reject decision for detector 1.1 |
| 5. Complete backend exercises | 28–40 | 1; can occupy collection waits | Tested upload → analysis → versioned results |
| 6. Persistent review workflow | 18–28 | 4 decision + 5 | Surviving artifacts, corrections, connected Streamlit flow |
| 7. Release evidence | 8–12 | 6 | Demo, research note, engineering report, ownership defense |

Maintain one active coding task at a time. During collection waits, work on Stage 5. Do not tune a detector using held-out results. If a stage runs over twice its estimate, reduce optional scope or revise estimates before starting another subsystem.

## 4. Review focus

1. A historical report still contains confident sequence wording: Stage 1 must apply current presentation rules even when loading old JSON.
2. A reference event is not visible: Stages 2–3 must record unlabelable status rather than manufacture a frame.
3. A failed detection disappears from an average: Stage 3 must retain it in the denominator and report missingness.
4. A stale worker finishes after a retry starts: Stage 5 must reject obsolete result writes.
5. A correction or artifact is lost after restart: Stage 6 must verify persistence without overwriting originals.

## Stage 1 — Correct claims and freeze the baseline

**Files:** modify `app.py`, `analyze_pitch_timing.py`, `generate_research_report.py`, `summarize_pitch_reports.py` where claims are emitted; add `tests/test_report_claims.py`, `docs/measurement_contract.md`, `docs/verification.md`. Inspect other callers with `rg` before editing.

**Contract:** foot contact and release are estimated visible events; pelvis/shoulder curves are exploratory image-plane proxies. Existing `pelvis_peak_frame` retains its legacy onset meaning. Add `pelvis_rotation_onset_frame` as an explicit alias. Present sequence interpretation as unsupported for coaching, including for old saved reports.

- [ ] Record the current source revision, detector/configuration, dependency versions, and a checksum manifest of a selected private baseline session. Keep raw participant media out of Git.
- [ ] Add failing tests for sequence wording in both newly generated and historical reports. Assert no “correct sequence” or “sequencing issue” conclusion appears; assert the unsupported status and proxy definition appear.
- [ ] Apply the presentation rule to UI, exported reports, and overlays. Keep historical raw numerical outputs available for reproducibility.
- [ ] Verify legacy keys remain readable and the onset alias agrees exactly with the old key. Do not change detector thresholds in this task.
- [ ] Run root tests; record the exact command and results. Add a root-test CI job so these tests are exercised on relevant changes.
- [ ] Save the baseline outputs before any later detector changes; update the ownership log and commit this independently.

**Why first:** the product currently makes a stronger interpretation than its own study supports. Correcting that demonstrates scientific judgment immediately.

## Stage 2 — Build independent labels

**Files:** add `tools/label_frames.py`, `docs/annotation_guide.md`, `docs/collection_protocol.md`, `tests/test_annotation_records.py`; extend `pitch_labels.py` and its tests only for additive metadata validation.

**Data contract:** retain v2 fields; add explicit `session_id`, `camera_id`, clip identity/checksum, annotator, pass, timestamp, blind flag and per-event status (`labeled`, `unlabelable`, `not_attempted`). For labeled events store an original-frame index; unlabelable events store no invented frame. Store review corrections separately from blind reference annotations.

- [ ] Define FFS as first visible lead-foot contact that persists, and BR as the first frame showing separation of ball and fingers. Include ambiguous and occluded examples. These definitions differ from force-plate contact and wrist-speed peaks.
- [ ] Implement a small raw-frame labeling tool with ±1/±10 frame stepping, original frame number, save/resume and annotator/pass selection. Do not load detector outputs in this tool.
- [ ] Add tests for saving/resuming without losing another pass, out-of-range frames, duplicate identity, and unlabelable events. Use atomic file replacement for labels.
- [ ] Plan an initial collection target of 5 athletes × 2 sessions × 10 pitches = 100 pitches, one side-view camera. This is a feasibility pilot target, not a power calculation or proof of population generalization.
- [ ] Assign 2 athletes to development and 3 to held-out evaluation before labeling/tuning; keep all sessions, views and frame-rate variants of one athlete in the same split. Existing P01 stays development; include P01 in the two development athletes if available.
- [ ] Obtain applicable permission/consent and institutional guidance before recruiting research participants; record allowed use and publication of footage. Arrange a second annotator.
- [ ] Blind A1 pass on all clips; A2 independently labels a stratified 30% subset across athletes/sessions; A1 repeats that subset after at least 7 days, shuffled. Preserve existing anchored labels as development history.
- [ ] Verify original FPS, timestamps, visibility and frame indexing. Reject or explicitly preprocess variable-frame-rate material with a preserved time map; do not assume frame/fps is valid for every uploaded file.

**Fallback:** with only your own footage, evaluate within-person/session behavior and say so. Backend work can continue; unseen-athlete claims cannot.

## Stage 3 — Produce the evaluation that the app will expose

**Files:** extend `evaluate_pitch_accuracy.py`; add `research/rq1_summary.py`, `tests/test_rq1_summary.py`, `docs/experiments/rq1-protocol.md`, `docs/test_runs.md`; update `research/obp_summary.py` and the RQ2 report generation.

**Evaluation row:** pitch UID, athlete, session, view, source clip/FPS, evaluated FPS, event, method/version, reference pass, reference status, predicted frame/status, signed ms error and absolute ms error. Failed predictions remain rows. Predictions on unlabelable references are reported separately, not scored as zero error.

- [ ] Before looking at held-out outcomes, write the question, splitting rule, baselines, metrics and decision rule into the protocol.
- [ ] Evaluate the frozen current detector and a minimal wrist-speed/ankle-motion baseline through the same evaluator. No access to reference events during prediction.
- [ ] Report detection coverage, median absolute error, signed bias, P90 error, within-10-ms fraction, and counts by event/FPS/view. Give both eligible-reference and successful-prediction denominators where applicable.
- [ ] Report A1/A2 and A1 repeat differences in milliseconds and agreement plots. Resample athletes for uncertainty; warn that three held-out athletes yield unstable population uncertainty. Sessions/trials/frames are not independent athletes.
- [ ] Measure the error of the derived FFS-to-BR interval directly. Do not infer interval accuracy by adding two median event errors.
- [ ] Derive 120/60/30 fps versions from original 240 fps for a controlled sensitivity study. Preserve original timestamps and map references explicitly. State that decimation does not reproduce longer-exposure motion blur.
- [ ] Add hand-calculated test fixtures for missing detections, unlabelable references, frame/time conversion, split leakage and group counts. Tests must reject a subject appearing in both dev and held-out sets.
- [ ] Reconcile the RQ2 48.8% versus raw 49.8% discrepancy by checking whether the intended column is oracle or end-to-end; generate the table from the chosen column and label it. Include the missing release value in coverage.
- [ ] Publish a versioned local JSON/CSV summary plus Markdown report generated in one documented command. Do not hand-copy result percentages into UI code.

**Exit:** a complete, reproducible report is required; high accuracy is not. Poor performance changes the product to assisted manual review and defines the next experiment.

## Stage 4 — Test one justified detector change

**Files:** `analyze_pitch_timing.py`, relevant callers in `auto_detect_pitch_windows.py`, `app.py`, `research/obp_simulation.py`, `robustness_stress_harness.py`, and backend `RealAnalyzer.ANALYSIS_ARGS`; extend `tests/test_signals.py`.

**Question:** does defining smoothing and ankle-stability support in milliseconds reduce frame-rate/noise sensitivity without degrading visible-event accuracy?

- [ ] Keep detector 1.0.0 and its frame-based behavior reproducible. Develop an explicit new-version configuration; do not silently change old output semantics.
- [ ] Introduce `window_frames(duration_ms: float, fps: float) -> int` with positive-input validation, documented rounding and a minimum of one frame. Choose any odd-window convention explicitly where smoothing requires it.
- [ ] Test equivalent physical-duration signals at 30/60/120/240 fps, short clips, missing landmarks, both throwing hands and noise. At 240 fps a five-frame support is about 21 ms; at 30 fps it is about 167 ms.
- [ ] Compare a small predefined set of durations (initial proposal: 25/50/100/150 ms) on development data, using the same trials for baseline and candidate. Stop after this experiment; do not start a broad model search.
- [ ] Proposed promotion rule, fixed before evaluation: neither event's development median absolute error worsens by more than 5 ms, coverage does not fall by more than 2 percentage points, and at least one preselected FPS/noise weakness improves. These are engineering tolerances, not literature-derived accuracy standards.
- [ ] Freeze candidate settings and evaluate held-out athletes once. Log every held-out evaluation. A held-out failure rejects or restricts the claim; do not keep tuning against those same outcomes.
- [ ] Save an ablation table and decision even if detector 1.0.0 remains the release default.

**Why this experiment:** the repo already identifies a concrete frame-rate-dependent failure. A measured accepted or rejected fix is stronger evidence than adding a model without a demonstrated need.

## Stage 5 — Complete the existing backend, then close reliability gaps

**Owner:** Ziyu, supported by explanation/review. Follow existing exercise signatures and API schemas. Existing tests are the initial contract, not proof of complete production safety.

| Task | Files | Acceptance |
|---|---|---|
| 5.1 Models | `backend/app/models/pipeline.py`, exports, migration 0002 | Exercise 1; constraints and upgrade/downgrade on disposable DB |
| 5.2 Lifecycle | `backend/app/jobs/state.py` | Exercise 2; legal transitions, retry bounds, terminal states |
| 5.3 Sessions/upload | `backend/app/api/sessions.py`, `videos.py` | Exercise 3; streamed size limits, parent validation, file cleanup |
| 5.4 Deduplication | `backend/app/services/idempotency.py`, `videos.py` | Exercise 4; concurrent submissions resolve to one active job |
| 5.5 Worker/results | `backend/worker/tasks.py`, `app/api/jobs.py` | Exercise 5; claim transaction, work outside transaction, atomic success |
| 5.6 Recovery | `backend/app/jobs/reaper.py`, `backend/worker/run.py` | Exercise 6 plus failure cases below |
| 5.7 Version selection | `backend/app/api/results.py`, `admin.py` | Exercise 7; explicit old/new versions, deterministic latest selection |

- [ ] For each exercise: run its tests to see the failures, implement, rerun that file, run non-exercise checks, record defense answers and commit. Do not fill the ownership log before doing the work.
- [ ] Run integration tests only against disposable PostgreSQL/Redis instances: the existing fixture drops the public schema and flushes Redis. Verify test destinations before running.
- [ ] Add a test for DB commit followed by enqueue failure. Implement bounded reconciliation of queued-but-undelivered work so it eventually runs; duplicate queue messages must remain harmless.
- [ ] Add a stale-attempt test: attempt A pauses, is reclaimed, B starts, then A returns. Capture attempt number on claim and condition success/failure writes on the matching current attempt/status under lock. Obsolete A cannot overwrite B.
- [ ] Align worker/reaper/runtime budgets. Current reaper default is 900 s, while each real-analyzer subprocess permits 1800 s and a job can contain many subprocesses. Define a total job deadline and recovery grace before real-video use; test timeout and retry behavior.
- [ ] Prove a requested detector version is the version actually executed. Reject mismatched queued jobs after deployment/version change, or keep the matching worker available; never label current-code outputs as an old version.
- [ ] After completion, make the exercise CI job required and remove informational failure tolerance. Extend type checking to `worker/` if retaining mypy as a release gate.
- [ ] On the isolated backend test environment run `python -m pytest tests`, `ruff check .`, `mypy`, and `python scripts/progress.py`. Require 7/7 completed; coverage is supporting evidence, not a replacement for recovery tests.

**Why use this scaffold:** it already defines the learning sequence, API shapes, race tests and ownership record. Replacing it would spend time without closing the real implementation gap.

## Stage 6 — Preserve evidence and connect the app

**Files:** `backend/app/analyzers.py`, `storage.py`, `schemas.py`, `models/pipeline.py`, worker/results handlers; new migrations after 0002; new `backend/app/api/artifacts.py`, `corrections.py`; `app.py`; tests `backend/tests/test_artifact_persistence.py`, `test_corrections.py`, `test_real_pipeline.py`.

**Persistence contract:** add a per-job manifest containing source revision, detector version, effective configuration, input checksum, environment, and artifact entries `{kind, storage_key, sha256, bytes, window_index}`. Artifact paths are generated server-side. Store named heuristic quality labels in the report, not as uncalibrated numeric probabilities.

**Correction contract:** append-only event corrections containing pitch/event identity, original automatic frame, corrected frame, author label, time and reason. Local author labels provide provenance, not authenticated identity. Preserve automatic events; effective review results overlay the latest correction. Independent blind labels never get silently replaced by review edits.

- [ ] Write a failing persistence test: after `RealAnalyzer.analyze` returns and its temporary directory is gone, selected JSON, landmark CSV, plot and overlay artifacts remain readable.
- [ ] Copy artifacts to attempt-scoped durable storage before the temp context exits; only the winning attempt's manifest becomes the job's authoritative result. Failed copies prevent successful completion. Provide cleanup for unreferenced attempt artifacts.
- [ ] Add `GET /jobs/{job_id}/artifacts` and `GET /jobs/{job_id}/artifacts/{artifact_id}`. Resolve only stored keys; test path traversal rejection, missing files, and checksum mismatch handling.
- [ ] Add `POST /pitches/{pitch_id}/corrections` and `GET /pitches/{pitch_id}/corrections`. Validate event names and frame bounds; append corrections transactionally. Use an additive correction table rather than rewriting Event rows.
- [ ] Test two corrections, restart, retrieval, raw-event preservation and historical version selection. Mark corrected summaries clearly and recalculate FFS-to-release duration from effective frames.
- [ ] Add a small API client boundary to Streamlit; wire session/upload → queued/running status → results → review → save correction → export. Use polling that does not rerun analysis on every Streamlit rerender.
- [ ] Keep local-script mode available during migration. Label the chosen execution mode explicitly; do not silently fall back and create results outside the backend history.
- [ ] Provide three accessible views: Review, Validation, Run details. Validation reads generated study summaries; Run details shows the selected job manifest. Do not imply a simulation interval validates an individual real-video prediction.
- [ ] Run one real private clip through the complete backend, restart services, reopen it and inspect the same results and correction. Separately test malformed footage, no detected pitch and an analyzer failure.

**Release behavior:** reviewers can finish a session even when automation fails, using clearly labeled manual review. Low-quality clips produce a useful explanation, not a confident biomechanics conclusion.

## Stage 7 — Verify the release and package your contribution

**Files:** `README.md`, `backend/README.md`, `docs/backend_ownership.md`, `docs/adr/`, `docs/case-study.md`, generated research and load-test reports.

- [ ] Exercise the full demo: analyze a permitted clip, inspect estimated events, correct one event, export, restart and retrieve the same version. Show a failure case as well as a successful example.
- [ ] Run the existing fixed-fake-analyzer scaling experiment with 1/2/4 workers and repeat each condition three times. Report environment, duration, queue wait/end-to-end latency, failures and spread; label it backend-only throughput.
- [ ] Measure real-video runtime separately on three fixed clips, documenting duration, resolution, FPS, hardware and detector config. Do not extrapolate fake-analyzer throughput into MediaPipe performance.
- [ ] Generate the validation tables from saved results. Include participant/session counts, unsuccessful detections, reference agreement, held-out limitations and reproducibility instructions.
- [ ] Write five decisions: database uniqueness, queue/transaction boundaries, stale-attempt handling, detector/result provenance, and limits of single-camera interpretation.
- [ ] Write a two-page case study: problem, personal contribution, method, measured results, failed hypothesis, limitations and next question. Retain assisted/scaffolded attribution.
- [ ] Prepare a 3-minute demo and a 10-minute technical explanation. Defend one detector failure, one concurrency failure and one statistical design choice without reading generated text.

**Done means:** tests/checks pass in their documented environments, one real session survives restart, data and report claims agree, correction history is preserved, and Ziyu can explain the work. A beautiful dashboard alone does not close the milestone.

## 5. The first four working weeks

Assume four hours each week; adjust around coursework.

| Week | Two-hour block 1 | Two-hour block 2 | Evidence at end |
|---|---|---|---|
| 1 | Reproduce tests and baseline manifest | Define allowed measurements and failing report tests | Recorded baseline and explicit claim contract |
| 2 | Correct report/UI/overlay wording | Regression check and documentation | Stage 1 complete, or a specific remaining failure |
| 3 | Raw-frame label tool and save/resume | Annotation protocol and metadata validation | Demonstrable blind labeling workflow |
| 4 | Label a small feasibility set independently | Review ambiguity with second annotator; arrange collection | Revised protocol and collection schedule |

If collection cannot start, work on backend Exercise 1 after the labeling task is complete. Do not substitute existing anchored labels for independent evaluation.

## 6. Later gates

After this release, choose one next research question. A non-baseball public benchmark is valuable for the career roadmap's transfer requirement, but dataset/task selection needs separate verification. RQ3/world landmarks should follow only if depth ambiguity remains the next limitation and there is a credible comparison protocol. Larger learned models require adequate independent subjects and a demonstrated baseline limitation. Sensors require a question video cannot answer.

## 7. Verification limits and self-review

Completed for this plan: inspected actual stubs/callers/contracts; ran all 20 root tests; counted local labels; independently aggregated selected saved simulation outputs; checked Docker availability; matched stages to ownership, measurement and workload constraints.

Not completed: backend integration suite, current CI run, full simulation rerun, new participant collection, real end-to-end video run, public deployment or external benchmark validation. Installation/version compatibility of a fresh backend environment is a Stage 5 setup check. Hour estimates and proposed promotion tolerances are recommendations, not verified empirical facts.

Self-review: claims precede UI expansion; blind labels precede tuning; original data survive corrections; legacy semantics remain explicit; backend retries are attempt-safe; held-out failures are retained; every stage has inspectable completion evidence. No new model or frontend rewrite is needed to satisfy this release.
