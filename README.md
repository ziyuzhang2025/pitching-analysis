# Baseball Pitching Timing Analysis MVP

## Project Overview

This project is a local-only baseball pitching timing analysis MVP. It uses
OpenCV to read a pitching video frame by frame and the local MediaPipe Pose
Python API to estimate body landmarks.

The goal is to help inspect basic pitching sequence timing:

- front foot strike
- pelvis peak rotation
- trunk peak rotation
- approximate ball release

Everything runs on your local machine. There is no cloud API and no API key.

## Current Features

- Local video analysis
- Pose landmark extraction
- Shoulder/hip angle calculation
- Angle unwrapping
- Front foot strike manual calibration
- Front foot strike confidence and debug signals
- Pelvis/trunk peak search windows
- Approximate ball release from throwing wrist speed
- Automatic pitch window detection
- Pose overlay video with event and 2D separation annotations
- Event review frames
- Multi-report summary CSV

## Tech Stack

- Python
- OpenCV
- MediaPipe Pose local Python API
- NumPy
- Pandas
- Matplotlib

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Streamlit UI

Run the local browser-based UI:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The Streamlit app is local-only. It can scan a full video with
`auto_detect_pitch_windows.py`, run analysis for each detected pitch, and show a
separate tab for every pitch with the pose overlay video, angles plot, readable
timing report, and raw JSON. A manual single-window analysis workflow remains
available in an expander for debugging calibrated clips.

## Automatic Pitch Window Detection

Use `auto_detect_pitch_windows.py` to scan a full local video and suggest likely
pitch windows before running detailed timing analysis:

```bash
python auto_detect_pitch_windows.py videos/test_pitch.MP4 --throwing-hand right --output-prefix test_pitch_auto --max-windows 1
```

This writes:

- `outputs/test_pitch_auto_pitch_windows.json`

The detector is an MVP heuristic based on throwing wrist speed, pelvis/trunk
rotation activity, and MediaPipe pose landmark visibility. A second-stage
validation filter scores each candidate with a simple pitch-likeness score so
general movement is less likely to be selected as a pitch. It does not train a
model and does not use any cloud service. Use `--run-analysis` to automatically
call `analyze_pitch_timing.py` for each detected window.

Automatic pitch window detection is still heuristic and may produce false
positives. It works best when the video contains clear full pitching motions,
good pose visibility, and limited unrelated movement.

## Example Workflow

Step 1: Generate a check overlay for a short section of video.

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --output-prefix pitch_03_check
```

Review:

- `outputs/pitch_03_check_pose_overlay.mp4`
- `outputs/pitch_03_check_angles_plot.png`
- `outputs/pitch_03_check_timing_report.json`

Step 2: Manually find the true front foot strike frame.

Use the overlay video or exported review frames to identify the original video
frame where the lead foot lands. Manual frame numbers should use the original
video frame number, not the trimmed clip frame number.

Step 3: Run windowed analysis with the manually calibrated front foot strike.

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --front-foot-strike-frame 2851 --pelvis-peak-search-end-ms 250 --trunk-peak-search-end-ms 300 --output-prefix pitch_03_windowed --export-event-review
```

Review:

- `outputs/pitch_03_windowed_pose_overlay.mp4`
- `outputs/pitch_03_windowed_review_frames/`
- `outputs/pitch_03_windowed_timing_report.json`

Step 4: Summarize trusted reports.

```bash
python summarize_pitch_reports.py --filename-contains windowed --require-manual-front-foot-strike
```

This writes:

- `outputs/pitch_summary_filtered.csv`

## Example Commands

Automatically suggest a likely pitch window:

```bash
python auto_detect_pitch_windows.py videos/test_pitch.MP4 --throwing-hand right --output-prefix test_pitch_auto --max-windows 1
```

Generate a check overlay:

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --output-prefix pitch_03_check
```

Run an analysis that includes approximate ball release:

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --output-prefix pitch_03_release
```

Run calibrated, windowed timing analysis:

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --front-foot-strike-frame 2851 --pelvis-peak-search-end-ms 250 --trunk-peak-search-end-ms 300 --output-prefix pitch_03_windowed --export-event-review
```

Summarize trusted windowed reports:

```bash
python summarize_pitch_reports.py --filename-contains windowed --require-manual-front-foot-strike
```

## Front Foot Strike Evaluation

Evaluate automatic front foot strike detection against the manually labeled
ground truth frames included in `evaluate_front_foot_strike.py`:

```bash
python evaluate_front_foot_strike.py
```

This runs `analyze_pitch_timing.py` automatically for each labeled pitch without
passing `--front-foot-strike-frame`, then writes:

- `outputs/front_foot_strike_evaluation.csv`

## Ball Release Evaluation

Evaluate automatic ball release detection against the manually labeled release
frame included in `evaluate_ball_release.py`:

```bash
python evaluate_ball_release.py
```

This runs `analyze_pitch_timing.py` automatically without passing
`--ball-release-frame`, then writes:

- `outputs/ball_release_evaluation.csv`

## Accuracy Evaluation

Evaluate automatic pitch event detection against manually labeled ground truth
frames from a labels JSON file:

```bash
python evaluate_pitch_accuracy.py --labels labels/pitch_labels.example.json --throwing-hand right --output-prefix eval_accuracy
```

The script runs `analyze_pitch_timing.py` for each labeled pitch window without
manual event overrides, compares automatic frames against the labeled
front foot strike, pelvis peak, trunk peak, and ball release frames, then writes:

- `outputs/pitch_accuracy_evaluation.csv`

Use `labels/pitch_labels.example.json` as a template and replace the example
frame numbers with manually reviewed labels for your own videos.

## Sample Result

Example terminal output from a filtered report summary:

```text
Reports included after filtering: 3
Correct sequence count: 3
Median FFS to pelvis: 183.4 ms
Median pelvis to trunk: 33.3 ms
Median FFS to trunk: 250.1 ms
```

## Outputs

The main analysis script creates:

- `outputs/landmarks.csv`
- `outputs/timing_report.json`
- `outputs/angles_plot.png`
- `outputs/pose_overlay.mp4`

With `--output-prefix pitch_03_windowed`, those become:

- `outputs/pitch_03_windowed_landmarks.csv`
- `outputs/pitch_03_windowed_timing_report.json`
- `outputs/pitch_03_windowed_angles_plot.png`
- `outputs/pitch_03_windowed_pose_overlay.mp4`

With `--export-event-review`, the script also creates JPEG review frames around
the selected event frames:

- `outputs/pitch_03_windowed_review_frames/`

With `--export-all-review-frames`, the script exports every 5th processed frame:

- `outputs/pitch_03_windowed_all_review_frames/`

The report summarizer creates:

- `outputs/pitch_summary.csv`
- `outputs/pitch_summary_filtered.csv` when filters are used

## What The Analyzer Measures

For every processed frame, the landmark CSV saves x, y, and visibility values
for:

- left shoulder
- right shoulder
- left hip
- right hip
- left ankle
- right ankle
- left wrist
- right wrist

The script also calculates:

- raw shoulder line angle
- raw hip line angle
- unwrapped shoulder line angle
- unwrapped hip line angle
- smoothed shoulder angle
- smoothed hip angle
- shoulder angular velocity
- hip angular velocity
- lead ankle x velocity
- lead ankle y velocity
- lead ankle speed
- lead ankle stability score
- throwing wrist x velocity
- throwing wrist y velocity
- throwing wrist speed
- hip-shoulder separation 2D proxy

Angle unwrapping helps avoid artificial jumps when angles cross the -180/180
degree boundary.

Hip-shoulder separation is reported as a signed shortest-angle 2D proxy in
degrees, limited to approximately -180 to +180. It is the camera-view 2D angle
difference between the shoulder line and hip line, not true 3D torso-pelvis
separation. The signed value can flip near +/-180 degrees, so the absolute
separation values and quality warning in `timing_report.json` should be used
when interpreting this metric.

Raw signed and absolute 2D separation can still be misleading because they do
not know whether the pelvis or shoulder/trunk is leading. Directional
hip-shoulder separation estimates the pelvis-opening direction and then reports
pelvis-leading separation in that direction. Positive directional separation
means the pelvis is leading the shoulder/trunk in the detected opening
direction. Negative or opposite-direction values are not treated as valid max
stretch values. This is still a 2D camera-view proxy, not true 3D
hip-shoulder separation.

The pose overlay video displays signed and absolute 2D hip-shoulder separation
values on each frame. It also displays the 2D pelvis line angle and
shoulder/trunk line angle used to compute the separation proxy. Delivery-window
max separation is searched from front foot strike through the frame before trunk
peak; this can expose an early max before pelvis peak, which may indicate early
trunk rotation. Stretch-phase max separation is searched from pelvis peak
through the frame before trunk peak, which checks the expected pelvis-to-trunk
stretch window. The overlay marks these with `MAX DIR DELIVERY SEP` and
`MAX DIR STRETCH SEP` labels. These are still 2D camera-view proxies, not true 3D
torso-pelvis separation.

Throwing arm metrics are also 2D camera-view proxies based on the throwing-side
shoulder, elbow, and wrist landmarks. They are useful for visual review of arm
slot and rough timing, but they should not be interpreted as true shoulder
external rotation, true layback, elbow torque, or elbow force.

## Metric Definitions / Limitations

Raw line angles are image-coordinate angles from the video frame:

- right = 0 degrees
- down = 90 degrees
- up = -90 degrees
- left = +/-180 degrees

These raw angles are useful for internal calculations and trends, but they are
not direct biomechanical angles. Forearm vs horizontal is easier to interpret:
when the forearm is parallel to the ground, it should be close to 0 degrees.
Forearm vs vertical is also easier to interpret: when the forearm is vertical,
it should be close to 0 degrees.

The arm slot proxy is still a 2D camera-view proxy, not true 3D arm slot.
The layback proxy is not true shoulder external rotation.

## Event Detection

Front foot strike is approximated automatically from the lead ankle:

- right-handed pitcher: lead foot is the left ankle
- left-handed pitcher: lead foot is the right ankle

The automatic detector is a simple rule-based score. It looks for:

- the lead ankle becoming stable for several frames
- lead ankle speed dropping below a threshold
- lead ankle y velocity changing from downward motion to stable motion
- hip/shoulder angular velocity increasing within the next 300 ms
- acceptable lead ankle landmark visibility

The timing report includes:

- `front_foot_strike_confidence`
- `front_foot_strike_auto_candidates`
- `front_foot_strike_debug_reason`

Because automatic front foot strike detection can be unreliable, the script
supports manual calibration:

```bash
--front-foot-strike-frame 2851
```

Pelvis and trunk peaks are searched inside a limited time window after front
foot strike so follow-through frames are less likely to be selected. Defaults:

- `--peak-search-start-ms 0`
- `--pelvis-peak-search-end-ms 300`
- `--trunk-peak-search-end-ms 350`

Manual `--pelvis-peak-frame` and `--trunk-peak-frame` values can override the
automatic peak search when needed.

Ball release is an approximation based on the throwing-side wrist:

- right-handed pitcher: `right_wrist`
- left-handed pitcher: `left_wrist`

The script searches from `--ball-release-search-start-ms 30` to
`--ball-release-search-end-ms 250` after trunk peak and selects the frame with
maximum throwing wrist speed. Use `--ball-release-frame` to manually override
this approximation.

Ball release confidence is included in `timing_report.json`. Low confidence
means the selected wrist-speed peak may be ambiguous, at the edge of the search
window, or based on low-visibility wrist landmarks, so the release frame should
be visually confirmed in `pose_overlay.mp4` or the event review frames.

## Sequence Classification

The analyzer does not assume every pitch has correct mechanics. It detects the
observed event order and reports a diagnostic sequence classification:

- `pelvis_then_trunk`: pelvis peak clearly occurs before trunk peak.
- `pelvis_trunk_near_simultaneous`: pelvis and trunk peaks are within +/-2 frames.
- `trunk_before_pelvis`: trunk appears to peak before pelvis by more than 2 frames.
- `peak_before_front_foot_strike`: a rotation peak appears before front foot strike.
- `unclear`: the sequence could not be classified confidently.

When pelvis and trunk peaks are within +/-2 frames, the app reports them as
near-simultaneous rather than simply correct or clear trunk-before-pelvis. A
single-camera 2D video may not resolve the true order at that frame-level
spacing, so the overlay should be reviewed visually.

## Limitations

- 2D single-camera analysis only
- MediaPipe landmarks can be noisy
- Not medical advice
- Does not calculate elbow force
- Does not calculate layback yet
- Ball release detection is approximate and based on wrist speed only
- Not using OpenBiomechanics/Driveline reference data yet

This is a first-pass timing tool, not a validated biomechanics model.

## Future Work

- More accurate ball release detection
- Layback angle
- Hip-shoulder separation
- Better front foot strike auto detection
- Multi-angle video support
- Comparison against reference biomechanics data
