# Baseball Pitching Timing Analysis MVP

## Project Overview

This project is a local-only baseball pitching timing analysis MVP. It uses
OpenCV to read a pitching video frame by frame and the local MediaPipe Pose
Python API to estimate body landmarks.

The goal is to help inspect basic pitching sequence timing:

- front foot strike
- pelvis peak rotation
- trunk peak rotation

Everything runs on your local machine. There is no cloud API and no API key.

## Current Features

- Local video analysis
- Pose landmark extraction
- Shoulder/hip angle calculation
- Angle unwrapping
- Front foot strike manual calibration
- Front foot strike confidence and debug signals
- Pelvis/trunk peak search windows
- Pose overlay video
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

Generate a check overlay:

```bash
python analyze_pitch_timing.py videos/IMG_1322.MOV --throwing-hand right --start-time 46 --end-time 48 --output-prefix pitch_03_check
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

Angle unwrapping helps avoid artificial jumps when angles cross the -180/180
degree boundary.

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

## Limitations

- 2D single-camera analysis only
- MediaPipe landmarks can be noisy
- Not medical advice
- Does not calculate elbow force
- Does not calculate layback yet
- Not using OpenBiomechanics/Driveline reference data yet

This is a first-pass timing tool, not a validated biomechanics model.

## Future Work

- Ball release detection
- Layback angle
- Hip-shoulder separation
- Better front foot strike auto detection
- Multi-angle video support
- Comparison against reference biomechanics data
