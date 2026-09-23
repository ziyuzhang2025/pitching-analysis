# PitchTiming Research Guide (agent-facing)

> **Status (2026-09-23): Phase 0 code done (not yet frozen); Phase 4 done; Phase 8 scaffold done, exercises waiting for Ziyu.** See Section 13 before starting work.

> **Purpose of this file.** This is the operating manual for any AI agent (Claude, Codex, etc.) or human working on this repository. Its goal is to turn the existing single-camera pitching timing MVP into a **validated, research-grade portfolio piece** (a short paper, a reproducible repo, a demo). Load this whole file into context before doing any work. It was written and fact-checked on **2026-09-23**. Section 11 lists what was verified and how.
>
> **Owner:** Ziyu (SMU Information Systems undergraduate). The career goal is a master's and later a job in sports performance technology / biomechanics ("using technology to push human performance"), connected to baseball. SWE and data skills are the fallback and the entry ticket.

---

## 0. Rules for the agent

1. **Read this file completely before starting a task.** Then read `CODEX_HARNESS.md`. Where the two conflict, this file wins for the phases defined here. The harness constraints that still hold: local-only processing, no API keys, no injury-risk / elbow-force / "true 3D" claims from 2D data, no silent threshold changes, backward-compatible outputs.
2. **Work one phase at a time** (Section 5). A phase is done only when every acceptance criterion has been checked on real artifacts, not just when the code compiles.
3. **Never invent numbers.** Every number in the paper, README, or resume must come from a script output that is committed or reproducible. Use `<TBD>` until then.
4. **Protect the test set.** Once Phase 0 freezes the detector, never look at test-set results while tuning. Tune only on the dev set (Section 5, Phase 0.4).
5. **Run the regression baseline before and after any detector change** (command in Section 2.3) and report the comparison.
6. **Ask the user before**: recording or using video of anyone other than Ziyu; publishing any video; pushing to GitHub; changing the research questions; spending money.
7. **Commit at the end of each sub-task** with a clear message. Don't push unless asked.
8. **Environment.** The code runs on Ziyu's Mac in `.venv` (Python + `mediapipe==0.10.21`). Command prefix used so far: `MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python`. If you are running in the Cowork Linux VM (`device_bash`), note that the Mac `.venv` will not run there, and `mediapipe` is **not** installed there (checked 2026-09-23). Either install into a separate Linux venv, or ask Ziyu to run MediaPipe steps on the Mac. OBP-only work (Phase 4) needs no MediaPipe and can run anywhere.
9. **Privacy.** `videos/`, `outputs/`, and `labels/pitch_labels.json` are git-ignored. Keep it that way. Only publish sample clips with written consent from the person in them.
10. **Backend work (Phase 8) is in teaching mode.** Ziyu writes the parts assigned to him (8.0). The agent scaffolds, explains, and reviews, and never silently fills in his parts.

---

## 1. The end product

| Layer | What it is | Audience |
|---|---|---|
| **Short paper** (4–6 pages, PDF, LaTeX) | The core deliverable. A validation study (Section 3). | Master's admissions, professors, biomechanics hiring |
| **GitHub repo** | Clean package, one-command reproduction of every table and figure, tests, CI, README first screen with the result table and a demo GIF | Engineers, interviewers |
| **Demo video** (60–90 s) | Problem → system → evidence → one honest failure → next step (3D) | Anyone who has 1 minute |
| **Streamlit app** (existing, lightly polished) | Proof the system runs end to end | Supporting evidence only |
| **PitchLab API** (Phase 8) | Async backend around the analyzer: FastAPI, Postgres, Redis workers, Docker, CI, load-test numbers, ADRs | Backend SWE interviewers |

**The central claim** the whole product must support (numbers to be filled in from results):

> From a single smartphone video, directly observable pitching events (front foot strike, ball release) can be detected within `<TBD>` ms of blind human annotators at 240 fps. Rotation-peak timing (pelvis/trunk) **cannot** be recovered reliably from a 2D image-plane proxy in a side view. We quantify this on 400+ lab-captured pitches and identify which camera views, frame rates, and proxies make it feasible.

The second half of that claim comes from verified pilot results (Section 3.3). A negative result, clearly measured, makes the paper stronger, not weaker.

---

## 2. Current state of the repo (verified 2026-09-23)

### 2.1 Code

| File | Lines | Role |
|---|---|---|
| `analyze_pitch_timing.py` | 2909 | Main analyzer: MediaPipe Pose (legacy `mp.solutions.pose`, `model_complexity=1`), 10 landmarks (shoulders, hips, ankles, elbows, wrists; x, y, visibility only, **no z, no world landmarks**), angles, events, overlay video, JSON report |
| `auto_detect_pitch_windows.py` | 964 | Finds pitch windows in a full video (heuristic) |
| `evaluate_pitch_accuracy.py` | 326 | Runs the analyzer per labeled pitch without overrides, and writes `outputs/pitch_accuracy_evaluation.csv` |
| `evaluate_front_foot_strike.py`, `evaluate_ball_release.py` | 171, 157 | Older single-event evaluators with hard-coded labels |
| `pose_reliability_harness.py` | 305 | Reliability CSV + review queue |
| `robustness_stress_harness.py` | 285 | Jitter/dropout stress test |
| `generate_research_report.py` | 284 | Markdown report from the above |
| `summarize_pitch_reports.py` | 194 | Summary CSV across reports |
| `app.py` | 1612 | Streamlit UI incl. manual correction → "Save corrected frames as ground-truth label" |

### 2.2 How events are currently defined in code (important)

- **Front foot strike (FFS):** rule-based score on lead-ankle stability, speed, vertical velocity, and subsequent rotation activity (`detect_front_foot_strike`).
- **Pelvis "peak":** `detect_pelvis_peak` selects the **first frame whose |hip-line angular velocity| ≥ max(120°/s, 25% of window max) and is rising**. That is the *onset of a strong rotation burst*, **not** peak angular velocity. The name and the definition disagree.
- **Trunk peak:** frame of max |`shoulder_angular_velocity`| in its search window (FFS + 0 … 350 ms by default), via `peak_in_frame_window` in `build_timing_report`. That is a true peak. **Pelvis and trunk therefore use different rules** (pelvis = onset, trunk = peak). This inflates the apparent pelvis→trunk gap and must be fixed or reported (Section 4).
- **"Angles"** are image-plane angles of the left–right hip line and shoulder line (`line_angle_degrees` on x, y). They are 2D projections, not axial rotation.
- **Ball release (BR):** frame of max throwing-wrist 2D speed, 30–250 ms after trunk peak.

### 2.3 Data and results

- Videos: `test_pitch_01.MP4`, `test_pitch_02.MP4`: 720×1280 portrait, **30 fps**, about 80 s each. The camera is a **side view**, and both appear to show **one right-handed pitcher** (confirm with Ziyu). `IMG_1322.MOV`: 3840×2160, 60 fps. `test_pitch.MP4`: 1280×720, 30 fps.
- Labels: `labels/pitch_labels.json`, **10 pitches** (5 per video). Most have `label_source: manual_streamlit`, meaning they were **corrected starting from the algorithm's output**.
- Current result (`outputs/phase3_validation_report.md`): mean absolute frame error FFS 0.0, pelvis 1.5, trunk 0.5, BR 0.1 frames.
- Regression baseline command (from `CODEX_HARNESS.md`):
  ```bash
  MPLCONFIGDIR=/private/tmp/mplconfig .venv/bin/python evaluate_pitch_accuracy.py \
    --labels labels/pitch_labels.json --throwing-hand right --output-prefix baseline_before_change
  ```

### 2.4 Known defects (fix in Phase 0)

1. **Output-prefix collision:** `pitch_output_prefix` uses only `pitch_id`. Both videos use `window_1..5`, so the second video's artifacts overwrite the first's (confirmed: duplicate `output_prefix` values in `pitch_accuracy_evaluation.csv`). The metrics are still correct because each row is computed right after its run, but the artifacts are lost.
2. **Single `--throwing-hand` for the whole label file.** Multi-pitcher data needs a per-pitch `throwing_hand`.
3. **Old evaluators** (`evaluate_front_foot_strike.py`, `evaluate_ball_release.py`) hard-code labels. Deprecate them in favor of `evaluate_pitch_accuracy.py`.
4. README "Future Work" lists hip-shoulder separation, which already exists. The "Sample Result" section is stale.
5. Scripts sit flat in the repo root, and there are no unit tests.

---

## 3. Why the study is designed this way (the logic)

### 3.1 The evaluation design problems in the current result

1. **Anchored labels.** The labels were made by correcting the algorithm's output, so agreement is inflated. FFS at 0.0 error on 10/10 is a symptom.
2. **No held-out data.** The commit history ("Improve pitching event detection accuracy", 2026-06-15, made right after the labels were added) indicates that the detector was tuned on the same 10 pitches it is evaluated on. Treat the current numbers as training error.
3. **Narrow sample:** one pitcher, one view, one frame rate, 10 pitches.
4. **30 fps is too coarse** (Section 3.2).
5. **Human labels for pelvis/trunk "peaks" are not valid ground truth.** Peak angular velocity is a property of a signal and cannot be seen in a single frame. A human "labeling" it is just guessing from the same visual cues. **Only visually observable events (FFS, BR, optionally maximum knee height) may be human-labeled.** Signal-derived events must be validated against lab data (Phase 4).

### 3.2 Verified fact: the pelvis→trunk gap is tiny

From the OpenBiomechanics Project (OBP) POI file (`poi_metrics.csv`, 411 pitches, 100 athletes, mostly college level; column `timing_peak_torso_to_peak_pelvis_rot_velo`), computed 2026-09-23:

| Statistic | Pelvis→torso peak delay |
|---|---|
| Median | **8.3 ms** |
| IQR | 0.0 – 16.7 ms |
| Share < 16.7 ms (one 60 fps frame) | 75% |
| Share < 33.3 ms (one 30 fps frame) | 89% |
| Share negative (torso peaks first) | 20% |

Peak pelvis velocity: median 742°/s. Peak torso: median 1050°/s.

**Consequence:** at 30 fps the sequence is below the sampling resolution for about 89% of pitches, so "pelvis then trunk" claims from 30 fps video are not supportable. Note that the current labels show 1–3 frames (33–100 ms) between pelvis and trunk. That is much larger than the lab distribution. Likely reasons: (a) the detector compares pelvis *onset* with trunk *peak* (Section 2.2); (b) the 2D proxy measures something different (Section 3.3); (c) the population differs. The paper should discuss this.

### 3.3 Verified pilot: 2D side-view proxies on lab data

Method (reproducible code in Appendix A): take OBP 3D joint centers (360 Hz), project them to a virtual camera looking along the lab y-axis (a pure side view, orthographic), resample to 30/60/120/240 fps with a random phase, and smooth with a centered 5-sample moving average (matching the analyzer default). Then find the peak |angular velocity| of the hip line and shoulder line between foot contact and ball release, and compare it with the true peak of `pelvis_velo_z` / `torso_velo_z` from `joint_velos.csv`. "Top" is an idealized overhead projection (the horizontal-plane angle from true 3D), an upper bound for any pseudo-3D method. No pose noise was added. n = 402 pitches.

| fps | Side-view hip-line peak error (median \|ms\|) | Top-view (3D horizontal) hip error | Side-view shoulder-line error | Top-view shoulder error |
|---|---|---|---|---|
| 30 | 24.6 | 27.8 | 55.9 | 12.5 |
| 60 | 26.4 | 11.8 | 43.5 | 18.0 |
| 120 | 27.7 | 4.0 | 45.4 | 26.4 |
| 240 | 27.5 | **2.7** | 45.0 | 27.9 |

Correct pelvis-before-trunk ordering: side view 54–66%, top view 64–69%.

A second pilot compared the peak 3D wrist-joint-center speed with the true ball release (OBP `BR_time`). It occurs a median **13.9 ms before** release (IQR −16.7 to −11.1 ms). Hand joint center: 8.4 ms before. The BR detector therefore has a **systematic early bias**. It is invisible at 30 fps, but at 240 fps it is about 3 frames.

**What the pilot tells us:**
- The side-view image-plane hip-line proxy has a **~25–28 ms systematic error that higher fps does not fix**. It is a proxy problem, not a sampling problem.
- A horizontal-plane (pseudo-3D) hip angle becomes accurate as fps rises (2.7 ms at 240 fps). That motivates using MediaPipe **world landmarks** (Phase 5).
- The shoulder-joint-center line is a poor stand-in for thorax rotation (scapular and arm motion contaminate it). The trunk proxy needs a better definition. Candidates: the mid-shoulder-to-mid-hip vector, or restricting the search window to before arm acceleration.
- The sequence (pelvis before trunk) cannot be reliably determined from joint-center lines even with ideal 3D data at these gap sizes. Report sequence classification as unreliable unless the gap exceeds a stated threshold.
- **Caveats:** a single pilot, with no noise, one smoothing choice, and one side azimuth. Phase 4 must reproduce and extend it before anything is claimed.

### 3.4 Research questions

- **RQ1 (real video, observable events):** How accurately can FFS and BR be detected automatically from a single smartphone video compared with blind human annotators, and how does accuracy change across frame rate (240/120/60/30) and camera view?
- **RQ2 (lab data, signal events):** How well can single-view 2D proxies recover pelvis and trunk peak-velocity timing and their order? How do error and ordering accuracy depend on camera azimuth, frame rate, and landmark noise?
- **RQ3 (improved proxy):** Does a pseudo-3D horizontal-plane rotation angle (from MediaPipe world landmarks) reduce the timing error compared with the 2D image-plane angle? Evaluate the idealized version on OBP and the real version on phone video.
- **RQ4 (optional):** What is the within-pitcher, pitch-to-pitch reliability of the timing metrics?

The argument chain for the paper is: *motivation → ground truth is trustworthy (human agreement) → algorithm vs humans on held-out data (RQ1) → generalization across views and fps → what a single camera cannot measure and why (RQ2) → a better proxy (RQ3) → limits and the path to multi-camera 3D.*

---

## 4. Event definitions (operational; put these in the paper and in `docs/annotation_guide.md`)

| Event | Definition for human annotators | Lab analogue (OBP) |
|---|---|---|
| **FFS** (front foot strike) | First frame in which any part of the lead foot is visibly in contact with the ground and stays in contact | `fp_10_time` (10% bodyweight on the force plate). Note that visual contact and 10% BW are not identical. Say so. |
| **BR** (ball release) | First frame in which a visible gap exists between the ball and all fingers | `BR_time` |
| **MKH** (max knee height, optional) | Frame in which the lead knee reaches its highest vertical image position | `pkh_time` |
| **Pelvis peak** | *Signal-defined only.* Frame of max pelvis axial rotation velocity between FFS and BR. **Not human-labeled.** | argmax `pelvis_velo_z` |
| **Trunk peak** | *Signal-defined only.* Frame of max trunk axial rotation velocity between FFS and BR. **Not human-labeled.** | argmax `torso_velo_z` |

Also rename the current code event `pelvis_peak_frame` → keep the key for backward compatibility, but add `pelvis_rotation_onset_frame` (the current "first strong rising" logic) and a true `pelvis_peak_velocity_frame` (argmax). Report both, and state clearly which one is being evaluated.

---

## 5. Phases

Rough effort assumes about 10 hours per week. If Ziyu is applying for a master's in the Fall 2027 cycle, deadlines typically fall around December 2026 – January 2027 (**verify per program**). In that case, prioritize Phases 0 → 4 plus a paper draft before the deadlines, and continue Phases 5 and 7 afterwards.

### Phase 0: Hygiene and freeze (≈1 week)

**0.1 Fix the output-prefix collision.** In `evaluate_pitch_accuracy.py`, build the prefix from the video stem and the pitch_id, e.g. `f"{base}_{Path(video).stem}_{pitch_id}"`. Keep old CSV columns. Add a new column `video_stem`.

**0.2 Labels schema v2** (backward compatible; the evaluator must still read v1):
```json
{
  "schema_version": 2,
  "pitches": [
    {
      "pitch_uid": "S01_P03_arm_240_w04",
      "video_path": "videos/S01/P03_arm_240.MOV",
      "pitcher_id": "P03",
      "throwing_hand": "right",
      "view": "arm_side",
      "fps": 240.0,
      "split": "test",
      "start_time": 12.10, "end_time": 13.90,
      "annotations": {
        "A1_pass1": {"front_foot_strike_frame": 2931, "ball_release_frame": 2977, "max_knee_height_frame": 2850, "labeled_at": "2026-10-20", "blind": true},
        "A1_pass2": {"...": "..."},
        "A2_pass1": {"...": "..."}
      },
      "reference": "A1_pass1"
    }
  ]
}
```
- `split` ∈ {`dev`, `test`}. `view` ∈ {`arm_side`, `glove_side`, `behind`, `front`}. Annotator IDs are A1 (Ziyu) and A2 (a second person).
- The evaluator uses per-pitch `throwing_hand` and falls back to the CLI flag.

**0.3 Unit tests** (`tests/`, pytest). Cover `line_angle_degrees`, `unwrap_angle_series_degrees`, `smooth_series`, `angular_velocity_degrees_per_second`, `frame_error`, the label loader (v1 and v2), and prefix uniqueness. Add a synthetic-signal test: a known sinusoidal rotation must yield a peak at the known frame.

**0.4 Dev/test split rule.** The existing 10 pitches and any footage used for tuning = `dev`. All new footage is assigned **per pitcher** to dev or test *before labeling* (for example, 1–2 pitchers dev, the rest test). Write the assignment into `labels/splits.json` and commit it.

**0.5 Freeze.** Run the baseline, save it as `outputs/baseline_detector-v1.0.csv`, and tag the commit `detector-v1.0`. From then on, any detector change requires dev-set evaluation only, followed by a new tag. The test set is evaluated **once per tag**, and every test run is logged in `docs/test_runs.md` (date, tag, and the result, even if it is bad).

**Acceptance:** tests pass; running the evaluator on the old 10 labels reproduces the numbers in `phase3_validation_report.md`; the prefix collision is gone (unique artifact files per pitch); the tag exists.

### Phase 1: Data collection protocol (≈1–2 weeks, mostly Ziyu's time)

**Participants.** Target ≥5 pitchers (≥3 minimum), ≥10 pitches each, at least 1 left-hander if possible. **Written consent** covering (a) use in research and a portfolio and (b) whether a clip may be published. Keep a template in `docs/consent_template.md`. Record only a pitcher ID, handedness, and height; no names in the repo.

**Cameras.** Phone slow motion at **240 fps, 1080p** (most recent iPhones support this; confirm on the device). Use a tripod at about hip height (~1 m), and keep the camera 5–8 m away, so the whole body including the stride foot stays in frame through the follow-through. Use landscape orientation. Lock exposure and focus (long-press on iPhone). Shoot outdoors in daylight or in bright light, because 240 fps needs a lot of light.

**Views.** Two phones recording at the same time give two views per pitch at no extra pitching cost:
- `arm_side`: perpendicular to the pitching direction, on the throwing-arm side
- `glove_side` **or** `behind`: choose one based on space; `behind` = directly behind the pitcher along the pitching direction

No synchronization is needed, because views are analyzed independently.

**File hygiene.** Export the **original** file, via AirDrop "Include all photos data" or cable, and never through a messaging app. Sharing apps often re-encode slow motion to 30 fps. After import, check every file:
```bash
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,avg_frame_rate -of csv=p=0 FILE
```
Reject any file whose `avg_frame_rate` is not ≈240.

**Metadata.** Record `data/sessions.csv` with columns `session_id,date,location,pitcher_id,throwing_hand,height_m,view,device,fps,file,notes`.

**Scale reference.** Place an object of known length (for example a 1 m stick) in the pitching plane for one clip per session. It is not needed for timing, but it enables stride-length estimates later.

**Acceptance:** ≥50 pitches × 2 views recorded, every file passes the ffprobe check, and `sessions.csv` and the consent forms are complete.

### Phase 2: Annotation protocol (≈1–2 weeks)

**2.1 Blind labeling tool.** Add a "blind mode" to the Streamlit app, or write a small separate script (`tools/label_frames.py`). It shows **raw frames only**: no skeleton, no algorithm events, no angle plots. Frame stepping is ±1 / ±10, the frame number is displayed, and the output is saved to the v2 schema under the chosen annotator/pass key. The labeler must not be able to see algorithm outputs for that pitch.

**2.2 Annotation guide** (`docs/annotation_guide.md`). Include the definitions from Section 4, one example image per event, and rules for ambiguous cases. For example: if the foot is occluded, label the first frame with visible contact and flag `occluded: true`.

**2.3 Passes.**
- A1 (Ziyu) pass 1 on all pitches.
- A1 pass 2 at least **7 days later**, in shuffled order, on a random ≥30% subset (for intra-rater reliability).
- A2 (a teammate, briefed with the guide) pass 1 on the same ≥30% subset (for inter-rater reliability).
- **Reference label** = A1 pass 1. Also report results against A2.

**2.4 Pitch windows.** Use `auto_detect_pitch_windows.py` only to find the approximate start and end of each pitch window, and pad them generously (±1 s). Windows must not reveal event frames.

**Acceptance:** all pitches labeled for FFS and BR (and MKH if used); reliability subsets are complete; labels committed as `labels/pitch_labels_v2.json` (git-ignored if it contains private paths; commit a pseudonymized copy).

### Phase 3: Real-video evaluation, RQ1 (≈1–2 weeks)

**3.1 Frame-rate experiment.** For each 240 fps clip, create decimated versions by keeping every 2nd, 4th, or 8th frame (→ 120/60/30 fps). Implement this in code by frame index (`frame_idx % k == 0`) so the labels map exactly (`label // k`, with rounding documented). Limitation to state in the paper: decimation keeps the short 240 fps exposure, so real 30 fps footage has more motion blur.

**3.2 Metrics per event × fps × view:**
- Signed error in ms (bias) and absolute error in ms: mean, median, P90
- % within ±1 frame and within ±10 ms
- Detection rate (share of pitches where the event was found)
- **Human agreement** for the same subset: A1 vs A2, and A1 pass 1 vs pass 2, as MAE in ms, plus Bland–Altman bias and 95% limits of agreement
- ICC for the inter- and intra-rater frame labels (two-way model, absolute agreement, single measure; report the form, following Koo & Li 2016)
- Uncertainty: **95% bootstrap CIs resampling pitchers (clustered), not pitches**, with 2000 resamples

**3.3 Baselines** (must be run through the same evaluator):
- `B0` naive: FFS = frame of minimum lead-ankle y-velocity magnitude after the ankle's lowest point. BR = frame of max throwing-wrist speed over the whole window with no search constraints.
- `B1`: the current detector at `detector-v1.0`.
- `B2` (if developed on dev only): the detector with the BR bias correction from Section 3.3, with the correction estimated from the **dev** split only.

**3.4 Outputs.** Write `outputs/rq1_results.csv` (long format: pitch_uid, pitcher_id, view, fps, event, method, signed_ms, abs_ms) and `outputs/rq1_summary.json`. Figures: `paper/figs/rq1_error_by_fps.pdf` (box plots per event × fps, with a human-agreement band) and `rq1_bland_altman.pdf`.

**Acceptance:** the test split is evaluated exactly once per detector tag and logged; every number in the summary can be regenerated by one command (`python -m pitchtiming.eval.rq1 --config configs/rq1.yaml`).

### Phase 4: Lab-data simulation, RQ2 (≈2 weeks; no MediaPipe needed)

**4.1 Data.** The OpenBiomechanics Project, `drivelineresearch/openbiomechanics`. License: **CC BY-NC-SA 4.0**, plus an additional clause forbidding use by anyone employed by or associated with a professional sports organization or financial analysis firm. The work must stay non-commercial, cite OBP, and share derived data under the same license. (If Ziyu later works for a pro team, this data may not be used there.)

Download the release assets from tag `dataset-v1`. These direct URLs worked on 2026-09-23 without authentication:
```
https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/pitching_landmarks.zip    (~33 MB, landmarks.csv ~110 MB)
https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1/pitching_joint_velos.zip
https://raw.githubusercontent.com/drivelineresearch/openbiomechanics/main/baseball_pitching/data/poi/poi_metrics.csv
https://raw.githubusercontent.com/drivelineresearch/openbiomechanics/main/baseball_pitching/data/metadata.csv
```
Save them to `data/external/obp/` (git-ignored). Write `scripts/download_obp.sh` with sha256 checks.

**4.2 Verified schema facts:**
- `landmarks.csv`: 360 Hz (`time` step 0.0028 s), 411 pitches (`session_pitch`), a median of about 600 samples (≈1.66 s) per pitch. Joint centers in meters, lab frame (+x second base → home, +y toward first base, +z up): `shoulder_jc`, `glove_shoulder_jc`, `rear_hip`, `lead_hip`, `elbow_jc`, `wrist_jc`, `hand_jc`, `rear/lead_knee_jc`, `rear/lead_ankle_jc`, `glove_elbow_jc`, `glove_wrist_jc`, `glove_hand_jc`, `thorax_ap/dist/prox`, `centerofmass`. Event columns: `pkh_time`, `fp_10_time`, `fp_100_time`, `MER_time`, `BR_time`, `MIR_time`.
- `joint_velos.csv`: `pelvis_velo_z` and `torso_velo_z` (axial rotation velocity, + toward home plate), filtered with a 4th-order Butterworth low-pass at 20 Hz.
- `poi_metrics.csv`: 81 columns incl. `p_throws`, `pitch_speed_mph`, `max_pelvis_rotational_velo`, `max_torso_rotational_velo`, `timing_peak_torso_to_peak_pelvis_rot_velo` (seconds).
- `metadata.csv`: `user` (100 athletes), `playing_level` (4 levels, mostly college).

**4.3 Refactor prerequisite.** Make the detector functions accept a DataFrame of named 2D landmarks plus fps, independent of MediaPipe and video I/O. Name mapping from OBP to the analyzer uses `p_throws`: for a right-hander, lead = left and rear = right (`lead_hip` → `left_hip`, `glove_shoulder_jc` → `left_shoulder`, `shoulder_jc` → `right_shoulder`, `wrist_jc` → `right_wrist`, `lead_ankle_jc` → `left_ankle`, etc.). Mirror this for left-handers. The **same code** must run on OBP-projected data and on real MediaPipe data.

**4.4 Virtual camera.** Use an orthographic projection by default (and optionally a pinhole camera 6 m away as a check). Parameters:
- azimuth θ around the vertical axis: 0° = behind the pitcher looking toward home, 90° = arm-side view (sign depends on handedness), 180° = front; sweep in 15° steps
- elevation φ ∈ {0°, 10°}
- Image coordinates are normalized to [0, 1] by body height, so the analyzer's thresholds still behave sensibly (document how).

**4.5 Degradations** (full factorial or sensible subset):
- fps ∈ {30, 60, 120, 240}, resampled by linear interpolation onto a grid with a random phase
- Gaussian landmark jitter σ ∈ {0, σ_real/2, σ_real, 2σ_real}. **Estimate σ_real from real MediaPipe data** (the frame-to-frame residual after low-pass on dev clips of Ziyu's videos), and report it.
- Dropout ∈ {0, 5%}
- 10 random seeds per condition

**4.6 Outputs per pitch × condition** (long CSV `outputs/rq2_sim.csv`): pelvis-peak timing error (ms), trunk-peak error, gap error, order correct (bool), FFS error vs `fp_10_time`, and BR error vs `BR_time`. Report the "onset" and "peak" pelvis definitions separately.

**4.7 Figures:**
- Polar or line plot of median |pelvis error| vs azimuth, one line per fps (this answers "where should I put the phone?")
- Order accuracy vs true gap size (binned), which shows why a small gap is unresolvable
- BR bias distribution (wrist vs hand)

**4.8 Sanity check.** With θ = 90°, φ = 0°, no noise, and 5-sample smoothing, the side-view hip error should come out near the pilot numbers in Section 3.3 (~25–28 ms). If not, find out why before going further.

**Acceptance:** the pilot is reproduced; the full sweep runs from one command; results are summarized in `outputs/rq2_summary.json`; the figures are generated into `paper/figs/`.

### Phase 5: Improved proxy, RQ3 (≈1–2 weeks)

1. Extend `extract_landmarks` to also save `results.pose_world_landmarks` (MediaPipe legacy API; meters, origin at the hip center) as `*_wx, *_wy, *_wz`, plus image `z`. Put this behind a flag `--save-world-landmarks` so default outputs stay unchanged.
2. Compute a horizontal-plane pelvis angle: `atan2` of the hip vector projected on the ground plane. Up-axis = −world y in MediaPipe (verify empirically on a standing frame). Do the same for the trunk, using mid-shoulder vs mid-hip and the shoulder line.
3. On OBP: the idealized version is the "top" projection in the pilot. Add depth noise of realistic size to test degradation.
4. On real video: there is no ground truth for peaks, so evaluate (a) agreement between arm-side and glove/behind views of the **same pitch** (cross-view consistency) and (b) whether the timing relative to FFS and BR falls in the lab distribution. Present this as consistency evidence, not accuracy.

**Acceptance:** the default analyzer output is unchanged when the flag is off; the RQ3 table compares the 2D and pseudo-3D proxies on OBP (with CIs) and on real video (consistency).

### Phase 6: Paper (≈2 weeks, overlapping)

- **Format:** LaTeX in `paper/`, 4–6 pages, two columns (any standard conference template). Consider submitting later to the ISBS conference (International Society of Biomechanics in Sports, which publishes short proceedings papers) or posting a preprint to SportRxiv. **Check current deadlines and templates before promising anything.**
- **Title idea:** *How Much Pitching Timing Can a Single Smartphone Measure? Validation Against Human Annotators and 400+ Lab-Captured Pitches.*
- **Sections:** Abstract · 1 Introduction (kinematic sequence; the lab-cost gap; RQs) · 2 Related work (marker-based vs markerless pitching validation, smartphone pose estimation) · 3 Methods (capture, events, detector, OBP simulation, proxies, statistics) · 4 Results (RQ1–RQ3) · 5 Discussion (what a single camera can and cannot measure; camera placement recommendations) · 6 Limitations · 7 Conclusion and future work (two-camera 3D).
- **Required figures:** (1) pipeline diagram; (2) RQ1 error vs fps with a human-agreement band; (3) pelvis error vs azimuth; (4) order accuracy vs true gap; (5) one failure-case frame strip.
- **Required tables:** (1) dataset summary; (2) RQ1 main table (event × method × fps with 95% CI, plus human–human agreement); (3) RQ3 proxy comparison.
- **Writing rules:** every number traces to `outputs/*summary.json`; limitations are written plainly; no clinical or injury claims; cite OBP per its license.
- `make paper` (or `python scripts/build_paper.py`) regenerates all figures and tables, then compiles.

### Phase 7: Repo, demo, app (≈1–2 weeks)

- **Package layout:**
  ```
  pitchtiming/  (pose.py, signals.py, events.py, proxies.py, report.py, overlay.py)
  pitchtiming/eval/  (rq1.py, rq2_sim.py, stats.py)
  app/          (Streamlit)
  scripts/      (download_obp.sh, build_paper.py)
  configs/      (rq1.yaml, rq2.yaml)
  tests/
  paper/
  data/sample/  (consented clip + labels only)
  docs/         (annotation_guide.md, consent_template.md, test_runs.md, this guide)
  ```
  Keep the old CLI entry points as thin wrappers so existing commands still work.
- **CI:** GitHub Actions runs pytest plus a smoke test of the OBP simulation on 5 pitches (no MediaPipe or video in CI).
- **README first screen:** title → demo GIF → the claim in 2 sentences with real numbers → result table → links (paper PDF, demo video, app) → "Works well / Known limits".
- **Demo video storyboard:** 0–10 s problem · 10–30 s system running · 30–50 s evidence table animating, with human vs algorithm · 50–70 s one honest failure (e.g. 30 fps side view) · 70–90 s next step, two-camera 3D.
- **App:** optional deployment (Streamlit Community Cloud or Hugging Face Spaces). Warn users that uploads must be their own videos, and don't store uploads.

### Phase 8: Backend service "PitchLab API" (≈3–4 weeks at ~10 h/week; runs in parallel with Phases 1–3)

**Why.** Ziyu must be able to *do* backend SWE work and prove it in interviews, not just show a repo. This project has real backend problems that justify every component. Analysis is CPU-heavy and takes seconds to minutes per video. Videos are large. Jobs fail mid-run. The same file gets uploaded twice. Detector versions change, so stored results go stale.

**Scope: core, local-only.** FastAPI + PostgreSQL + Alembic + a Redis job queue + a worker that runs the existing analyzer + Docker Compose + pytest (unit and integration) + GitHub Actions CI + a load test. **Out of scope:** user accounts/auth, cloud deployment, paid services. Add them only if Ziyu asks.

**Relation to `CODEX_HARNESS.md`.** The harness forbids databases, auth, and deployment. That rule still applies to the **analysis core** (`analyze_pitch_timing.py` and the research scripts), which must stay importable and runnable without any backend. The backend lives in its own folder (`backend/`) and only *calls* the analyzer. It must not change detector logic.

#### 8.0 Teaching mode (mandatory for any agent)

The deliverable is Ziyu's skill, not only the code. Split the work:

| Owner | Work |
|---|---|
| **Agent** | Project skeleton, Dockerfiles, `docker-compose.yml`, CI workflow, config/settings module, logging setup, test fixtures, *one* fully worked example endpoint plus its tests (as a pattern to copy), the load-test harness, code review of Ziyu's work |
| **Ziyu writes** | The seven exercises in `docs/backend_exercises.md`: models + migration 0002; the state machine + retry policy; the sessions/upload endpoints; idempotency (service + `/analyze`); the worker task + jobs API; the reaper; results + backfill. Also all ADRs (8.8), in his own words. |

*As built (2026-09-23):* the `Athlete` model, migration 0001, and `/athletes` became the agent's fully worked example; `sessions`/`videos` onward are Ziyu's. Specs are the docstrings in each target file. The exercise tests are in `backend/tests/exercises/` (72 tests, pytest marker `ziyu`), and `python scripts/progress.py` shows the checklist. The tests were validated against a private reference implementation (all pass), which is shared with Ziyu only after he finishes (§8.0).

Rules:
- For Ziyu-owned items, the agent creates the file with a docstring spec, type signatures, and failing tests marked `# TODO(ziyu)`. Explain concepts and review diffs, but **do not write the implementation** unless Ziyu explicitly says "write it for me" for that specific item. If he does, record it in `docs/backend_ownership.md`, so it is clear which parts he wrote.
- After each Ziyu-owned item, run a short **defense check**: ask him 2–3 "why / what if" questions from 8.10 and note the answers in `docs/backend_ownership.md`.

#### 8.1 Architecture

```
Client ──► FastAPI (api) ──► PostgreSQL
              │  enqueue job_id
              ▼
            Redis ──► worker × N ──► analyzer (analyze_pitch_timing.py, unchanged)
                          │
                          └──► storage/ (local volume behind a Storage interface)
```

Layout:
```
backend/
  app/ (main.py, config.py, db.py, models.py, schemas.py, storage.py, queue.py, logging.py)
  app/api/ (athletes.py, sessions.py, videos.py, jobs.py, results.py, admin.py, health.py)
  worker/ (worker.py, tasks.py)
  migrations/ (Alembic)
  tests/ (unit/, integration/)
  loadtest/ (locustfile.py, README.md)
  Dockerfile.api, Dockerfile.worker, docker-compose.yml, pyproject.toml or requirements*.txt
docs/adr/  docs/backend_ownership.md
```
Pin exact library versions in a lock or requirements file when scaffolding. Record them in the README.

#### 8.2 Data model (PostgreSQL)

- `athletes(id, code UNIQUE, throwing_hand CHECK IN ('right','left'), height_m NULL, created_at)`
- `sessions(id, athlete_id FK, recorded_on DATE, location, notes, created_at)`
- `videos(id, session_id FK, sha256 CHAR(64), storage_key, filename, bytes, fps, width, height, view, created_at, UNIQUE(session_id, sha256))`
- `analysis_jobs(id, video_id FK, detector_version, status CHECK IN ('queued','running','succeeded','failed'), attempts INT, max_attempts INT, idempotency_key UNIQUE, error TEXT NULL, queued_at, started_at, finished_at, worker_id)`
- `pitches(id, job_id FK, window_index, start_frame, end_frame)`
- `events(id, pitch_id FK, name CHECK IN (...), frame, time_s, method ('auto'|'manual'), confidence NULL)`
- Indexes: `analysis_jobs(status, queued_at)`, `analysis_jobs(video_id, detector_version)`, `events(pitch_id, name)`.
- Every change goes through an Alembic migration. There must be at least one non-trivial second migration (for example, adding `view` to `videos` with a backfill), so the history shows a real schema evolution.

#### 8.3 API (REST, JSON, OpenAPI auto-docs at `/docs`)

- `POST/GET /athletes`, `GET /athletes/{id}`; `POST/GET /athletes/{id}/sessions`
- `POST /sessions/{id}/videos` (multipart upload; stream to storage while hashing; reject non-video types and files above a size limit); `GET /videos/{id}`
- `POST /videos/{id}/analyze` → 202 + job, with `Idempotency-Key` header support; `GET /jobs/{id}`; `GET /jobs?status=&limit=&cursor=`
- `GET /videos/{id}/results?detector_version=` (defaults to the latest succeeded)
- `POST /admin/reanalyze?detector_version=` (backfill: enqueue jobs for videos without results at that version)
- `GET /health` (DB + Redis reachable), `GET /metrics` (optional, Prometheus text)
- Conventions: cursor pagination; a single error shape `{"error": {"code", "message", "details"}}`; Pydantic validation; 404/409/422 used correctly.

#### 8.4 Job lifecycle and reliability

- State machine: `queued → running → succeeded | failed`. Only allowed transitions. Enforce them in one function with unit tests for every illegal transition.
- Retries: on exception, `attempts += 1`. Re-enqueue with exponential backoff plus jitter while `attempts < max_attempts`, else `failed` with the error stored.
- Crash safety: a job stuck in `running` longer than a timeout is re-queued by a reaper. Test this by killing a worker mid-job (integration test or scripted demo).
- The worker writes results in **one DB transaction**, so there are no half-written results.

#### 8.5 Idempotency and dedup

- Same `(session, sha256)` upload → return the existing video (200) instead of creating a duplicate.
- Same `Idempotency-Key`, or the same `(video_id, detector_version)` while a job is queued or running → return the existing job.
- Enforce with DB unique constraints (not only application checks), plus a test that fires concurrent duplicate requests.

#### 8.6 Versioned results

- Every result row is tied to `analysis_jobs.detector_version` (from `analyze_pitch_timing.DETECTOR_VERSION`) and stores the analyzer's `environment` block.
- Note on the environment: the worker container runs Linux. On Apple-silicon Docker that is linux/arm64, where `mediapipe==0.10.21` is not available (verified 2026-09-23: only ≤0.10.18 and 1.0.x install on aarch64). Pin a version that installs, record it, and **never mix backend results with the Mac-native research numbers.** The backend is a product demo; the paper's numbers come from `scripts/mac_baseline.sh` and later Mac runs.

#### 8.7 Testing, CI, observability

- Unit tests: the state machine, idempotency logic, schemas, storage.
- Integration tests: a real Postgres and Redis (Docker services in CI, or testcontainers), API → queue → worker using a **fake analyzer** that returns fixed events instantly. Add one slow, opt-in test with the real analyzer on a tiny clip.
- Test coverage report in CI. GitHub Actions: lint (ruff), type check (mypy on `backend/app`), tests.
- JSON logs with a request id carried from API to job. Health endpoint. Optional metrics: jobs by status, queue wait time, job duration.

#### 8.8 ADRs (Ziyu writes; ½ page each, in `docs/adr/`)

1. The queue choice: Redis + RQ vs Celery vs a Postgres `SELECT … FOR UPDATE SKIP LOCKED` table
2. Idempotency strategy
3. Versioned results and backfill
4. Local storage behind an interface (and how S3 would slot in)
5. Why the analyzer stays a library, not a service

#### 8.9 Load test and scaling result (the headline number)

- Locust: N users upload small clips and poll results. The worker uses the **fake analyzer with a fixed, realistic sleep** (for example the median real analysis time measured once), so the test measures the backend, not MediaPipe.
- Run 1, 2, and 4 workers. Report throughput (jobs/min), API p50/p95 latency, queue-wait p95, and the error rate. Put the table in the README and `docs/load_test.md` with the machine specs.
- Expected shape: throughput scales with workers until CPU-bound. Explain where it stops scaling and why.

#### 8.10 Defense checklist (Ziyu must answer these without notes)

1. 1000 users upload at once. What breaks first, and what would you change?
2. A worker dies halfway through a job. What happens to the job and the partial results?
3. The same video is uploaded twice in parallel. Walk through the exact code path and DB constraint.
4. You need to add a column to a table with a million rows. How do you migrate safely?
5. Detector 1.1 ships. How do old results stay valid, and how do you backfill?
6. Why a queue instead of running the analysis inside the request?
7. How do you test the worker without running MediaPipe?
8. Where are the transaction boundaries, and why there?

#### 8.11 Acceptance

- `docker compose up` starts api, worker, postgres, and redis; the README quickstart works from a clean clone.
- CI is green: ruff, mypy, unit and integration tests. Coverage of `backend/app` ≥ 80%.
- Kill-a-worker demo recovers; the concurrent duplicate test passes.
- The load-test table exists with real numbers.
- All 5 ADRs are written by Ziyu; `docs/backend_ownership.md` lists who wrote what, plus the defense-check notes.
- The analysis core still runs standalone, and `tests/` (the core tests) still pass.

**Resume bullet template** (fill in from the load test only):
"Built an async video-analysis backend (FastAPI, PostgreSQL, Redis workers, Docker) with idempotent uploads, retry with backoff, crash recovery, and versioned results; sustained `<X>` jobs/min at p95 API latency `<Y>` ms with 4 workers."

**Market note (checked 2026-09-23).** Across Singapore backend postings, Java appears most often (≈45%), then Python (≈29%). Common extras are Spring Boot, Kafka, microservices, CI/CD, and cloud (source: freehire.me Singapore backend role stats). Python is right for this project. For Java-heavy targets, a later small Spring Boot service (for example a read-only results API) can close the gap.

---

## 6. Guardrails: never claim these

- True 3D angles, hip-shoulder separation, arm slot, or layback from single-view 2D data (call them "2D proxies")
- Injury risk, elbow torque or force, or medical advice
- General accuracy from a small sample, or accuracy on the test set after tuning on it
- A "correct kinematic sequence" from 30 fps video
- Human labels of pelvis/trunk peaks as ground truth

---

## 7. Skills demonstrated → target roles

| Phase | Skills demonstrated | Roles this evidences |
|---|---|---|
| 0 | Refactoring, testing, versioning, reproducibility | SWE intern, ML/Research engineer |
| 1 | Experimental protocol, data collection, consent, metadata | Sports science / biomechanics research assistant, master's research labs |
| 2 | Annotation protocol, inter/intra-rater reliability | Data annotation lead, CV data engineer, research assistant |
| 3 | Validation statistics (Bland–Altman, ICC, clustered bootstrap), baselines, held-out evaluation | Data scientist/analyst, CV engineer intern, biomechanics analyst |
| 4 | Biomechanics data (OBP), 3D→2D projection, time-series signal processing, simulation experiments | **Biomechanics analyst (MLB R&D)**, applied biomechanics engineer, sports-tech R&D (Driveline, KinaTrax, Rapsodo-type companies) |
| 5 | Pose estimation internals, 3D geometry, proxy design | CV / 3D vision intern, perception research |
| 6 | Scientific writing, research communication | Master's admissions (SOP evidence), research roles |
| 7 | Packaging, CI, deployment, product communication | SWE intern, full-stack / AI systems |
| 8 | REST API design, relational modeling and migrations, async job queues, idempotency, retries and crash recovery, integration testing, Docker/CI, load testing, ADRs | **Backend SWE intern**, AI/ML platform or backend intern, full-stack |

Real-posting grounding (checked 2026-09-23):
- The Cleveland Guardians "Biomechanics Analyst, Baseball R&D" posting asks for R or Python, biomechanics data experience, and time-series modeling; it prefers SQL and knowledge of public biomechanics research.
- The MLB "Applied Biomechanics Engineer" posting asks for motion capture and force plates, 3D dynamics and inverse kinematics, reporting from large mocap datasets, three or more programming languages, and familiarity with markerless mocap and wearables.
- Phases 3–4 map directly onto these. Gaps this project does **not** close: inverse dynamics, OpenSim/Visual3D, and hands-on marker-based lab work. Those are the target of a master's.

**Resume bullets** (templates; fill in only with real numbers):
- Biomechanics / research: "Validated smartphone-based pitching event detection against blind human annotators on `<N>` pitches from `<P>` pitchers; FFS/BR error `<x>`/`<y>` ms at 240 fps vs. human–human `<z>` ms."
- Research / data: "Quantified the limits of single-view 2D rotation proxies using 400+ lab-captured pitches (OpenBiomechanics); showed side-view pelvis timing error of `<x>` ms that does not improve with frame rate, and identified camera placements that reduce it to `<y>` ms."
- CV: "Built a MediaPipe-based pipeline with pseudo-3D rotation proxies from world landmarks, reducing pelvis-peak timing error from `<x>` to `<y>` ms in simulation."
- SWE: "Refactored a 7k-line research codebase into a tested Python package with CI and one-command reproduction of all paper figures."

---

## 8. Timeline template

| Week | Work |
|---|---|
| 1 | Phase 0 |
| 1–3 | Phase 1 (recording sessions) in parallel with Phase 4 start (OBP needs no new data) |
| 3–4 | Phase 2 annotation (A1 pass 2 ≥7 days after pass 1) |
| 4–6 | Phase 4 complete; Phase 3 |
| 6–8 | Phase 5; paper draft (Phase 6) |
| 8–10 | Phase 7; paper revision; README/demo |
| 2–6 (parallel) | Phase 8 backend: week 2 skeleton + models; week 3 API + state machine; week 4 idempotency + tests + CI; week 5 load test + ADRs + defense check |

---

## 9. Definition of done (whole project)

- [ ] `detector-vX` tag; test set evaluated once per tag, logged in `docs/test_runs.md`
- [ ] ≥50 pitches, ≥3 pitchers, 2 views, 240 fps, blind labels, reliability subsets
- [ ] RQ1, RQ2, RQ3 summary JSONs, all generated by commands in the README
- [ ] Paper PDF with every number traceable
- [ ] Repo: package, tests, CI green, README first screen, a consented sample clip
- [ ] Demo video
- [ ] Limitations stated consistently in the paper, README, and app

---

## 10. Open decisions (ask Ziyu)

1. Application cycle and deadlines, which determine how the phases are prioritized.
2. Who will be A2 (the second annotator), and which pitchers.
3. Whether to use camera views `glove_side` or `behind` as the second view.
4. Whether to aim for a formal submission (ISBS / preprint) or keep the paper as a portfolio piece.

---

## 11. Verification log (2026-09-23)

| Claim | How verified |
|---|---|
| Repo structure, line counts, CLI flags, event logic (Section 2) | Read the source on Ziyu's machine (`grep` of `add_argument`, `def`; read `detect_pelvis_peak`, `add_calculations`, `extract_landmarks`, evaluator) |
| Videos: fps, resolution, side view, single pitcher | `ffprobe` on each file; viewed one extracted frame from each of test_pitch_01/02 (single-pitcher identity is a visual impression; confirm) |
| Label count and anchoring (`manual_streamlit`) | Read `labels/pitch_labels.json` |
| Current accuracy numbers | Read `outputs/pitch_accuracy_evaluation.csv` and `outputs/phase3_validation_report.md` |
| Output-prefix collision | Duplicate `output_prefix` values across videos in the evaluation CSV + `pitch_output_prefix` code |
| MediaPipe not installed in the Cowork Linux VM | `python3 -c "import mediapipe"` → ModuleNotFoundError |
| OBP license text incl. pro-team clause | Fetched the repo page |
| OBP schema, sample rates, events, filter settings | Read `baseball_pitching/README.md`; loaded `landmarks.csv`, `joint_velos.csv`, `poi_metrics.csv`, `metadata.csv` |
| Pelvis→torso gap statistics (Section 3.2) | Computed from `poi_metrics.csv` (411 rows) |
| Pilot projection and BR-bias results (Section 3.3) | Ran Appendix A code on OBP data (402 pitches with complete events) |
| Job requirements (Section 7) | Fetched the two postings linked in Section 12 |
| Appendix A code reproduces Section 3.3 table exactly | Extracted the code block from this file and ran it on OBP data |
| Trunk peak uses `peak_in_frame_window` (plain max) | Read `build_timing_report` (≈ lines 1792–1823) |
| Singapore backend market stats (Java ≈45%, Python ≈29%, etc.) | Fetched freehire.me Singapore backend role page on 2026-09-23 |
| `mediapipe==0.10.21` unavailable on linux/aarch64 (≤0.10.18, 1.0.x only) | `pip install` in the Cowork Linux VM |
| **Not verified:** exact ISBS deadlines and templates; phone 240 fps support on Ziyu's specific device; MediaPipe world-landmark axis convention (verify empirically in Phase 5); author lists of the related-work papers (verify before citing) | — |

---

## 12. References and links

- OpenBiomechanics Project: https://github.com/drivelineresearch/openbiomechanics (pitching docs: `baseball_pitching/README.md`)
- Comparison of marker-less and marker-based motion capture for baseball pitching kinematics, *Sports Biomechanics* 23(12): https://www.tandfonline.com/doi/full/10.1080/14763141.2022.2076608
- Validation of pitchAI markerless motion capture using marker-based 3D motion capture (PubMed 36409062): https://pubmed.ncbi.nlm.nih.gov/36409062/
- Variability of in-game markerless and laboratory marker-based baseball pitching biomechanics (PubMed 40418881): https://pubmed.ncbi.nlm.nih.gov/40418881/
- Assessing the accuracy of in-stadium and portable multi-camera markerless motion capture for baseball pitching, *J Sports Sci* (2025): https://www.tandfonline.com/doi/abs/10.1080/02640414.2025.2595411
- Role of pelvis and trunk biomechanics in generating ball velocity in baseball pitching (PubMed 35836313): https://pubmed.ncbi.nlm.nih.gov/35836313/
- Koo, T. K., & Li, M. Y. (2016). A guideline of selecting and reporting intraclass correlation coefficients for reliability research. *Journal of Chiropractic Medicine*, 15(2), 155–163.
- Bland, J. M., & Altman, D. G. (1986). Statistical methods for assessing agreement between two methods of clinical measurement. *The Lancet*, 327(8476), 307–310.
- Singapore backend role stats: https://freehire.me/roles/backend/singapore
- Job postings: Cleveland Guardians Biomechanics Analyst: https://sportstechjobs.com/biomechanics-analyst-baseball-research-and-development-cleveland-guardians/667c77791faf20c5797ea379 ; MLB Applied Biomechanics Engineer: https://simplify.jobs/p/d8ffcddf-0c49-41b2-a04d-e74b54e1c3d6/Applied-Biomechanics-Engineer

---

## Appendix A: Pilot code (reproduces Section 3.3)

```python
# Requires landmarks.csv and joint_velos.csv from OBP (Section 4.1). numpy, pandas only.
import numpy as np, pandas as pd
lm = pd.read_csv("landmarks.csv"); jv = pd.read_csv("joint_velos.csv")
lm["session_pitch"] = lm.session_pitch.astype(str); jv["session_pitch"] = jv.session_pitch.astype(str)
rng = np.random.default_rng(0)
smooth = lambda a, w=5: pd.Series(a).rolling(w, center=True, min_periods=1).mean().values
rows = []
for sp, g in lm.groupby("session_pitch"):
    j = jv[jv.session_pitch == sp]
    fp, br = g.fp_10_time.iloc[0], g.BR_time.iloc[0]
    if j.empty or not np.isfinite(fp) or not np.isfinite(br): continue
    w = (j.time >= fp) & (j.time <= br)
    if w.sum() < 3: continue
    tp = j.time[w].values[np.argmax(j.pelvis_velo_z[w].values)]   # true pelvis peak
    tt = j.time[w].values[np.argmax(j.torso_velo_z[w].values)]    # true trunk peak
    t = g.time.values
    for fps in [30, 60, 120, 240]:
        grid = np.arange(t[0] + rng.uniform(0, 1 / fps), t[-1], 1 / fps)
        I = lambda c: np.interp(grid, t, g[c].values)
        hx, hy, hz = (I(f"lead_hip_{a}") - I(f"rear_hip_{a}") for a in "xyz")
        sx, sy, sz = (I(f"glove_shoulder_jc_{a}") - I(f"shoulder_jc_{a}") for a in "xyz")
        m = (grid >= fp) & (grid <= br)
        def peak_t(a, b):
            ang = smooth(np.degrees(np.unwrap(np.arctan2(a, b))))
            vel = np.gradient(ang) * fps
            return grid[m][np.argmax(np.abs(vel[m]))] if m.sum() >= 2 else np.nan
        side_h, top_h = peak_t(hz, hx), peak_t(hy, hx)   # side view = project out y; top = horizontal plane
        side_s, top_s = peak_t(sz, sx), peak_t(sy, sx)
        rows.append(dict(sp=sp, fps=fps,
            side_hip=abs(side_h - tp) * 1e3, top_hip=abs(top_h - tp) * 1e3,
            side_sho=abs(side_s - tt) * 1e3, top_sho=abs(top_s - tt) * 1e3,
            side_order_ok=np.sign(side_s - side_h) == np.sign(tt - tp),
            top_order_ok=np.sign(top_s - top_h) == np.sign(tt - tp)))
r = pd.DataFrame(rows)
print(r.groupby("fps")[["side_hip", "top_hip", "side_sho", "top_sho"]].median().round(1))
print(r.groupby("fps")[["side_order_ok", "top_order_ok"]].mean().round(2))
```

BR-bias pilot: for each pitch, compute the 3D speed of `wrist_jc` and `hand_jc` (gradient over `time`), find the peak time within [`fp_10_time`, `BR_time` + 0.1 s], and subtract `BR_time`. Result: median −13.9 ms (wrist) and −8.4 ms (hand).

---

## 13. Status log

### 2026-09-23: Phase 0 (code) and Phase 4 complete. Branch `research/phase0-phase4`, not pushed.

**Done**
- `pitch_labels.py` (schema v1/v2 loader), `tools/migrate_labels_v1_to_v2.py`, `labels/splits.json` (P01 = dev), local `labels/pitch_labels_v2.json` (git-ignored; the existing 10 labels stored under annotation key `A1_anchored`)
- Evaluator: unique `pitch_uid` prefixes (fixes the collision), per-pitch hand, `--split`, `--annotation`, `--output-csv`, new columns appended
- Analyzer: `DETECTOR_VERSION = "1.0.0"`, `pelvis_rotation_onset_frame`, `pelvis_peak_velocity_frame`, definition strings, `environment`. Selected events are unchanged (timing reports diffed before/after).
- `tests/` (20 pytest tests, passing in the Linux VM), `requirements-dev.txt`
- `scripts/mac_baseline.sh`: official Mac baseline plus a comparison with the June numbers
- Phase 4: `scripts/download_obp.sh`, `research/obp_simulation.py` (sharded), `research/obp_summary.py`, results in `research/results/` (see `RQ2_FINDINGS.md`), figures in `paper/figs/`. Sanity check 4.8 passed: the side-view 2D true-peak pelvis error of 26.9 ms at 240 fps is consistent with the pilot's 27.5 ms.
- Removed a stale, empty `.git/HEAD.lock` dated 2026-07-02 (no git process was running).

**Waiting on Ziyu**
1. Run `bash scripts/mac_baseline.sh` on the Mac. If it prints ALL MATCH, tag `detector-v1.0` and merge the branch.
2. Data collection (Phase 1) and annotation (Phase 2).

**New findings that change the plan**
- The smoothing window (5 frames) and the FFS ankle thresholds are per-frame, so their behavior changes with fps. At 240 fps, FFS error rises from 16 to 58 ms with 0.3%-body-height landmark noise. Detector 1.1 should define windows in ms. Develop this on the **dev** set plus the OBP simulation, never on test.
- The current pelvis "onset" rule reports pelvis-first in 92.8% of pitches (lab truth: 68.9%). Sequence classification must not be reported.
- Best single-camera placement is about 60–90° from behind (Section 3 of `RQ2_FINDINGS.md`). **Change Phase 1 views to `arm_side` (90°) plus a rear-oblique of about 60°**, not directly behind.
- FFS and BR have about +15 ms systematic late bias at the side view. Estimate the correction on dev only.
- Orthographic projection makes θ and θ+180° identical. Occlusion is not modeled.

**Next automatable steps**
- Phase 3 code: fps decimation, baselines, clustered bootstrap, Bland–Altman, ICC; test with synthetic labels
- Blind labeling tool (Phase 2.1)
- Phase 5: `--save-world-landmarks`, then the ground-plane proxy on real video
- Detector 1.1 candidate (ms-based windows) evaluated on OBP plus dev
- Paper skeleton with the RQ2 section written

### 2026-09-23: Phase 8 (backend) added to the plan

- Ziyu wants to be able to do backend SWE work and show it. Chosen scope: **core backend, local-only** (no auth, no cloud deployment).
- Teaching mode is mandatory (Section 5, Phase 8.0, and rule 10). Next step: the agent scaffolds `backend/`, creates the Ziyu-owned files as specs with failing tests, and walks him through 8.2 (data model) first.

### 2026-09-23: Phase 8 scaffold built (commit fa2cf97 on `research/phase0-phase4`)

**Done (agent-owned per 8.0)**
- `backend/`: FastAPI app factory, settings, DB session, JSON logs with `X-Request-ID` (carried into worker logs via RQ job meta), the error shape, cursor pagination, streaming upload storage (sha256 while streaming, size limit, atomic rename), the RQ queue with delayed retries (scheduler), and analyzer adapters (`FakeAnalyzer`: fails on content starting with `FORCE_FAIL`; `RealAnalyzer`: runs the repo scripts in a temp dir). Also `worker/run.py` (scheduler + reaper thread), the `Athlete` worked example + migration 0001, and `/health` + `/version`.
- Docker: `Dockerfile.api`, `Dockerfile.worker` (optional real analyzer, mediapipe 0.10.18 on arm64), `docker-compose.yml` (postgres, redis, a one-shot migrate service, api, worker), and a repo-root `.dockerignore` (keeps videos/outputs out).
- CI: `.github/workflows/backend.yml` (ruff + mypy + non-exercise tests with coverage required; exercise progress informational).
- Load test: `loadtest/locustfile.py` (custom "JOB end_to_end" metric) and `loadtest/run_scaling.py` (compose or local mode, 1/2/4 workers, drains the backlog between runs, writes `summary.md`).
- Docs: `backend/README.md`, `docs/backend_exercises.md`, `docs/backend_ownership.md`, `docs/adr/`.

**Verified**
- In the cloud (Python 3.11, Postgres 16, Redis 7): ruff and mypy clean; 26 non-exercise tests pass (85% coverage); all 72 exercise tests fail on the stubs and pass on the reference.
- The race tests passed 6/6 runs on the reference, and a naive version without `IntegrityError` handling fails them 3/3.
- End to end with real uvicorn plus an RQ worker: the success path works, and a forced-failure job retried with backoff and ended `failed` after 3 attempts.
- Local load-test smoke run on the reference (2 CPUs, 1 s fake analysis): 39 jobs/min with 1 worker, 75 with 2. This only proves the harness works; it is **not** a portfolio number.
- On Ziyu's machine (Linux VM, Python 3.10): ruff, mypy, and the pure unit tests pass, and the app imports. The core `tests/` still pass (20).
- **Not verified:** Docker images were not built (Docker Hub is blocked from the agent's environment; only `docker compose config` was validated), and GitHub Actions has not run (nothing pushed). The first `docker compose up --build` on the Mac is the real test.

**Next (Ziyu):** install Docker Desktop, run `cd backend && docker compose up --build`, then start Exercise 1.
