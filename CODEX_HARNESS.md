# Codex Harness: Pitching Analysis Reliability Upgrades

## Objective

Improve the local-only baseball pitching timing project in three deliberate
phases. The goal is to make the existing 2D video analysis workflow more
reliable, interpretable, and research-ready without changing its scope into a
3D biomechanics, injury-risk, elbow-force, cloud, or machine-learning project.

Work through the phases in order. Complete and validate one phase before
starting the next. Do not combine unrelated refactors with a phase.

## Project Context

- Main analyzer: `analyze_pitch_timing.py`
- Auto pitch windows: `auto_detect_pitch_windows.py`
- Accuracy evaluator: `evaluate_pitch_accuracy.py`
- Local UI: `app.py`
- Inputs and outputs are local files only.
- Pose estimation uses the local MediaPipe Python API.
- Existing manually labeled pitches are stored under `labels/`.
- Current event accuracy has been validated on 10 labeled pitches. Treat this
  as a baseline to protect, not as proof of broad generalization.

## Non-Negotiable Constraints

- Keep all processing local-only. Do not add an API key, cloud service,
  database, authentication, or deployment work.
- Do not add ML training in these phases.
- Do not add elbow force, injury-risk, true 3D arm slot, true shoulder external
  rotation, or true 3D hip-shoulder separation claims.
- Do not silently change event detection thresholds or mechanics calculations.
- Preserve current command-line workflows and existing output formats whenever
  possible. New fields and outputs are acceptable if backward compatible.
- Treat every separation, arm slot, and layback-related value as a 2D
  camera-view proxy in user-facing text.
- Do not update the Streamlit UI unless a phase explicitly requires it.
- Use `apply_patch` for code edits. Do not revert user changes.

## Baseline Before Any Detector Change

Before changing `analyze_pitch_timing.py` or event logic in any later task:

```bash
MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python \
  evaluate_pitch_accuracy.py \
  --labels labels/pitch_labels.json \
  --throwing-hand right \
  --output-prefix baseline_before_change
```

Record the resulting event errors. If a later detector change is proposed, run
the same evaluation afterward and report whether FFS, pelvis, trunk, or release
accuracy regressed. Do not claim an improvement without this comparison.

---

## Phase 1: Pose Reliability and Event Review Queue

### Goal

Make the system explain when a pitch or event should be reviewed manually.
This phase should not alter automatic event-frame selection.

### Required Work

1. Create a local reliability analysis workflow that reads existing
   `*_timing_report.json` and `*_landmarks.csv` files.
2. Assess at least:
   - video FPS
   - landmark detection rate
   - mean and low-percentile landmark visibility
   - front foot strike confidence
   - ball release confidence
   - whether pelvis, trunk, or release peaks are near their search-window edge
   - sequence classification
   - existing throwing-arm and separation quality warnings
3. Produce a prioritized review queue containing:
   - output/report identifier
   - review priority: `high`, `medium`, or `low`
   - concrete risk reasons
   - primary event to inspect
   - suggested frame range around that event
4. Make all threshold choices explicit in CLI help, code constants, or output
   metadata. Do not present them as medically validated thresholds.
5. Keep wording balanced. A low score means “review visually,” not “the
   detector failed.” Explicitly mention 30 fps limitations when relevant.

### Required Outputs

- A full reliability CSV under `outputs/`.
- A sorted manual-review queue CSV under `outputs/`.
- A JSON summary with priority counts and risk-reason counts.
- README usage documentation.

### Acceptance Criteria

- The workflow runs with only local existing outputs.
- Missing CSV/report fields yield `N/A` or a clear risk reason, not a crash.
- It does not overwrite landmarks CSVs, timing reports, plots, or overlay
  videos.
- It identifies at least one concrete visual review reason for intentionally
  low-confidence or low-FPS examples.

---

## Phase 2: Landmark Robustness Stress Test

### Goal

Measure how sensitive existing event detection is to plausible pose landmark
noise. This is a robustness experiment, not ground-truth accuracy evaluation.

### Required Work

1. Build a command-line workflow operating on an existing landmarks CSV and
   timing report.
2. In memory only, create perturbed copies with configurable:
   - normalized-coordinate Gaussian jitter
   - temporary landmark dropout / missing values
   - deterministic random seed
   - number of trials per condition
3. Reuse existing analyzer calculations and automatic event functions where
   practical. Do not duplicate or rewrite detector rules just for the test.
4. For every trial, record automatic FFS, pelvis peak, trunk peak, and ball
   release frames.
5. Compare each trial to the unperturbed automatic baseline and report:
   - detection fraction
   - mean absolute frame shift
   - median absolute frame shift
   - P90 absolute frame shift
6. Make clear that perturbation sensitivity is not equivalent to real-video
   accuracy against manual labels.

### Required Outputs

- Trial-level CSV under `outputs/`.
- JSON summary grouped by jitter and dropout condition.
- README usage documentation and scope warning.

### Acceptance Criteria

- With zero jitter and zero dropout, the baseline event shift is zero or any
  discrepancy is clearly reported.
- Source landmarks CSV and timing report remain unchanged.
- The script can run with a small test configuration such as two trials and two
  noise conditions.
- Output preserves enough metadata to reproduce the experiment: input files,
  FPS, throwing hand, seed, smoothing window, jitter levels, dropout rates, and
  trial count.

---

## Phase 3: Research-Ready Validation Report

### Goal

Turn local evaluator, reliability, and stress-test artifacts into a concise,
honest research report suitable for GitHub, a portfolio, or a professor email.

### Required Work

1. Create a local report generator that can consume:
   - `evaluate_pitch_accuracy.py` CSV output
   - Phase 1 reliability CSV
   - optional Phase 2 stress summary JSON
2. Generate Markdown and a machine-readable JSON summary.
3. Include:
   - scope and safety statement
   - input artifact paths
   - number of labeled pitches
   - per-event mean and median absolute frame error
   - within 1 / 3 / 5 frame percentages
   - reminder that 30 fps is approximately 33.3 ms per frame
   - reliability priority counts and common risk reasons
   - stress-test condition summaries when supplied
   - conservative next validation step
4. Use careful language:
   - “may indicate,” “review,” and “confirm visually” are preferred.
   - Do not claim general accuracy from a small validation set.
   - Do not describe 2D proxies as true 3D biomechanics.

### Required Outputs

- Markdown report under `outputs/`.
- JSON report summary under `outputs/`.
- README usage documentation.

### Acceptance Criteria

- The generator handles missing optional reliability/stress files without
  crashing.
- Missing metrics render as `N/A`.
- The report can be generated using only local files.
- The report is readable without opening source code.

---

## Validation Checklist

After each phase, run:

```bash
MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python -m py_compile \
  analyze_pitch_timing.py auto_detect_pitch_windows.py \
  evaluate_pitch_accuracy.py app.py
```

Also compile every new script added in that phase. For any code that changes
event detection, run the baseline accuracy evaluation before and after the
change, then report the comparison clearly.

## Final Delivery Format

For each completed phase, report:

1. Files changed or added.
2. Exact local commands run.
3. Output artifact paths.
4. Validation result.
5. Limitations and remaining human-review requirements.

Do not declare a phase complete merely because code compiles. Confirm that it
ran on a real local output artifact and produced the required files.
