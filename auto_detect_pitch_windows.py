#!/usr/bin/env python3
"""
Heuristic local pitch-window detector.

This script scans a full video with OpenCV and local MediaPipe Pose, then
suggests short windows likely to contain a pitch. It is intentionally simple:
no cloud API, no API key, and no machine learning training.
"""

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd


LANDMARK_NAMES = [
    "left_shoulder",
    "right_shoulder",
    "left_hip",
    "right_hip",
    "left_ankle",
    "right_ankle",
    "left_wrist",
    "right_wrist",
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Detect likely pitch windows in a local video."
    )
    parser.add_argument("video_path", help="Path to a local pitching video.")
    parser.add_argument(
        "--throwing-hand",
        choices=["right", "left"],
        required=True,
        help="Pitcher's throwing hand.",
    )
    parser.add_argument(
        "--output-prefix",
        default="auto_detected",
        help="Prefix for outputs/{prefix}_pitch_windows.json.",
    )
    parser.add_argument(
        "--max-windows",
        type=int,
        default=1,
        help="Maximum number of pitch windows to return.",
    )
    parser.add_argument(
        "--min-pitch-likeness",
        type=float,
        default=0.35,
        help="Minimum second-stage pitch-likeness score required for a window.",
    )
    parser.add_argument(
        "--max-overlap-ratio",
        type=float,
        default=0.4,
        help="Maximum allowed overlap ratio with a higher-scoring selected window.",
    )
    parser.add_argument(
        "--debug-candidates",
        action="store_true",
        help="Write a CSV with second-stage validation details for candidates.",
    )
    parser.add_argument(
        "--run-analysis",
        action="store_true",
        help="Run analyze_pitch_timing.py on each detected window.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for JSON output and optional analysis outputs.",
    )
    return parser.parse_args()


def throwing_wrist_name(throwing_hand):
    """Return throwing-side wrist landmark name."""
    return "right_wrist" if throwing_hand == "right" else "left_wrist"


def lead_ankle_name(throwing_hand):
    """Return lead ankle name for a right- or left-handed pitcher."""
    return "left_ankle" if throwing_hand == "right" else "right_ankle"


def line_angle_degrees(x1, y1, x2, y2):
    """Return image-coordinate line angle in degrees."""
    if any(pd.isna(value) for value in [x1, y1, x2, y2]):
        return np.nan
    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def unwrap_angle_series_degrees(angle_series):
    """Unwrap an angle series to reduce -180/180 discontinuities."""
    filled = angle_series.interpolate(limit_direction="both")
    if filled.isna().all():
        return filled

    radians = np.deg2rad(filled.to_numpy())
    unwrapped = np.unwrap(radians)
    return pd.Series(np.rad2deg(unwrapped), index=angle_series.index)


def coordinate_velocity(series, fps):
    """Calculate normalized coordinate velocity per second."""
    if fps <= 0 or len(series) < 2 or series.isna().all():
        return pd.Series(np.nan, index=series.index)

    filled = series.interpolate(limit_direction="both")
    velocity = np.gradient(filled.to_numpy()) * fps
    return pd.Series(velocity, index=series.index)


def normalize_series(series):
    """Scale a numeric series to roughly 0-1 using robust percentiles."""
    finite = series.replace([np.inf, -np.inf], np.nan).dropna()
    if finite.empty:
        return pd.Series(0.0, index=series.index)

    low = float(finite.quantile(0.10))
    high = float(finite.quantile(0.95))
    if high <= low:
        return pd.Series(0.0, index=series.index)

    normalized = (series - low) / (high - low)
    return normalized.clip(lower=0.0, upper=1.0).fillna(0.0)


def normalized_peak(value, median_value, high_value):
    """Normalize a peak value against median and high-percentile video activity."""
    if not np.isfinite(value) or high_value <= median_value:
        return 0.0
    return float(np.clip((value - median_value) / (high_value - median_value), 0.0, 1.0))


def safe_float(value, default=np.nan):
    """Convert a value to float without leaking NumPy scalar types into JSON."""
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def landmark_to_columns(name, landmark):
    """Convert a MediaPipe landmark to x/y/visibility columns."""
    if landmark is None:
        return {
            f"{name}_x": np.nan,
            f"{name}_y": np.nan,
            f"{name}_visibility": np.nan,
        }

    return {
        f"{name}_x": landmark.x,
        f"{name}_y": landmark.y,
        f"{name}_visibility": landmark.visibility,
    }


def video_metadata(video_path):
    """Read FPS, frame count, dimensions, and duration."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    if not fps or fps <= 0:
        raise RuntimeError("Could not read a valid FPS value from the video.")
    if total_frames <= 0:
        raise RuntimeError("Could not read a valid frame count from the video.")

    return float(fps), total_frames, total_frames / float(fps)


def extract_pose_landmarks(video_path, fps, total_frames):
    """Run local MediaPipe Pose on the full video and return landmark rows."""
    mp_pose = mp.solutions.pose
    pose_landmarks = mp_pose.PoseLandmark
    landmark_indices = {
        "left_shoulder": pose_landmarks.LEFT_SHOULDER.value,
        "right_shoulder": pose_landmarks.RIGHT_SHOULDER.value,
        "left_hip": pose_landmarks.LEFT_HIP.value,
        "right_hip": pose_landmarks.RIGHT_HIP.value,
        "left_ankle": pose_landmarks.LEFT_ANKLE.value,
        "right_ankle": pose_landmarks.RIGHT_ANKLE.value,
        "left_wrist": pose_landmarks.LEFT_WRIST.value,
        "right_wrist": pose_landmarks.RIGHT_WRIST.value,
    }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    rows = []
    print(f"Scanning {total_frames} frames for pitch activity...")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        frame_number = 0
        while True:
            success, frame_bgr = cap.read()
            if not success:
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)
            row = {
                "frame": frame_number,
                "time_seconds": frame_number / fps,
                "pose_detected": bool(results.pose_landmarks),
            }

            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                for name in LANDMARK_NAMES:
                    row.update(
                        landmark_to_columns(name, landmarks[landmark_indices[name]])
                    )
            else:
                for name in LANDMARK_NAMES:
                    row.update(landmark_to_columns(name, None))

            rows.append(row)
            frame_number += 1

            if frame_number % 300 == 0:
                print(f"Scanned {frame_number}/{total_frames} frames")

    cap.release()
    print(f"Scanned {len(rows)}/{total_frames} frames")
    return pd.DataFrame(rows)


def add_activity_signals(df, fps, throwing_hand):
    """Compute wrist speed, body rotation activity, visibility, and score."""
    df = df.copy()
    wrist = throwing_wrist_name(throwing_hand)

    wrist_x_velocity = coordinate_velocity(df[f"{wrist}_x"].astype(float), fps)
    wrist_y_velocity = coordinate_velocity(df[f"{wrist}_y"].astype(float), fps)
    df["throwing_wrist_speed"] = np.sqrt(wrist_x_velocity**2 + wrist_y_velocity**2)

    df["pelvis_angle_raw"] = df.apply(
        lambda row: line_angle_degrees(
            row["left_hip_x"],
            row["left_hip_y"],
            row["right_hip_x"],
            row["right_hip_y"],
        ),
        axis=1,
    )
    df["trunk_angle_raw"] = df.apply(
        lambda row: line_angle_degrees(
            row["left_shoulder_x"],
            row["left_shoulder_y"],
            row["right_shoulder_x"],
            row["right_shoulder_y"],
        ),
        axis=1,
    )

    pelvis_angle = unwrap_angle_series_degrees(df["pelvis_angle_raw"])
    trunk_angle = unwrap_angle_series_degrees(df["trunk_angle_raw"])
    pelvis_rotation = pd.Series(np.gradient(pelvis_angle.to_numpy()), index=df.index)
    trunk_rotation = pd.Series(np.gradient(trunk_angle.to_numpy()), index=df.index)
    df["rotation_activity"] = pelvis_rotation.abs() + trunk_rotation.abs()

    visibility_columns = [
        f"{wrist}_visibility",
        "left_hip_visibility",
        "right_hip_visibility",
        "left_shoulder_visibility",
        "right_shoulder_visibility",
        "left_ankle_visibility",
        "right_ankle_visibility",
    ]
    df["visibility_score"] = df[visibility_columns].mean(axis=1).fillna(0.0)

    wrist_component = normalize_series(df["throwing_wrist_speed"])
    rotation_component = normalize_series(df["rotation_activity"])
    visibility_component = df["visibility_score"].clip(lower=0.0, upper=1.0)
    df["pitch_activity_score_raw"] = (
        (0.50 * wrist_component)
        + (0.35 * rotation_component)
        + (0.15 * visibility_component)
    )

    smoothing_window = max(3, int(round(fps * 0.15)))
    df["pitch_activity_score"] = (
        df["pitch_activity_score_raw"]
        .rolling(window=smoothing_window, center=True, min_periods=1)
        .mean()
    )
    return df


def confidence_for_candidate(score, median_score, visibility):
    """Return a coarse confidence label for a candidate peak."""
    if visibility < 0.45 or score < median_score * 1.15:
        return "low"
    if visibility >= 0.70 and score >= median_score * 1.75:
        return "high"
    return "medium"


def get_peak_frame(item):
    """Return a peak frame from either candidate or selected window objects."""
    if "frame" in item:
        return item["frame"]
    if "candidate_peak_frame" in item:
        return item["candidate_peak_frame"]
    raise ValueError(
        "Candidate/window item is missing both 'frame' and 'candidate_peak_frame'."
    )


def window_overlap_ratio(first_window, second_window):
    """Return overlap ratio relative to the shorter of two time windows."""
    overlap_start = max(first_window["start_time"], second_window["start_time"])
    overlap_end = min(first_window["end_time"], second_window["end_time"])
    overlap = max(0.0, overlap_end - overlap_start)

    first_duration = max(0.0, first_window["end_time"] - first_window["start_time"])
    second_duration = max(0.0, second_window["end_time"] - second_window["start_time"])
    shorter_duration = min(first_duration, second_duration)
    if shorter_duration <= 0:
        return 0.0
    return overlap / shorter_duration


def generate_activity_candidates(df, fps):
    """Find local maxima in the original pitch activity score."""
    ignore_frames = int(round(0.5 * fps))
    candidates = []
    scores = df["pitch_activity_score"].to_numpy()
    start_index = ignore_frames
    end_index = max(ignore_frames, len(df) - ignore_frames)

    for position in range(start_index, end_index):
        previous_score = scores[position - 1] if position > 0 else -np.inf
        current_score = scores[position]
        next_score = scores[position + 1] if position + 1 < len(scores) else -np.inf
        if current_score >= previous_score and current_score >= next_score:
            candidates.append(
                {
                    "frame": int(df.iloc[position]["frame"]),
                    "score": float(current_score),
                    "position": position,
                }
            )

    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def lead_ankle_stability_score(window_df, fps, peak_time, throwing_hand):
    """Estimate whether the lead ankle settles shortly after peak activity."""
    ankle = lead_ankle_name(throwing_hand)
    after_peak = window_df[
        (window_df["time_seconds"] >= peak_time)
        & (window_df["time_seconds"] <= peak_time + 0.35)
    ]
    if len(after_peak) < max(2, int(round(0.10 * fps))):
        return 0.0

    x_range = after_peak[f"{ankle}_x"].astype(float).max() - after_peak[f"{ankle}_x"].astype(float).min()
    y_range = after_peak[f"{ankle}_y"].astype(float).max() - after_peak[f"{ankle}_y"].astype(float).min()
    motion_range = math.sqrt(safe_float(x_range, 0.0) ** 2 + safe_float(y_range, 0.0) ** 2)
    return float(np.clip(1.0 - (motion_range / 0.08), 0.0, 1.0))


def validate_candidate_window(
    df,
    candidate,
    fps,
    duration_seconds,
    throwing_hand,
    median_score,
    median_wrist_speed,
    high_wrist_speed,
    median_rotation_activity,
    high_rotation_activity,
    min_pitch_likeness,
):
    """Calculate second-stage pitch-like features for one candidate window."""
    candidate_peak_frame = get_peak_frame(candidate)
    candidate_time = candidate_peak_frame / fps
    start_time = max(0.0, candidate_time - 1.2)
    end_time = min(duration_seconds, candidate_time + 0.6)
    window_df = df[
        (df["time_seconds"] >= start_time) & (df["time_seconds"] <= end_time)
    ].copy()

    if window_df.empty:
        window_df = df.iloc[[candidate["position"]]].copy()

    wrist_series = (
        window_df["throwing_wrist_speed"]
        .astype(float)
        .replace([np.inf, -np.inf], np.nan)
    )
    rotation_series = (
        window_df["rotation_activity"]
        .astype(float)
        .replace([np.inf, -np.inf], np.nan)
    )
    wrist_peak_index = (
        wrist_series.idxmax() if not wrist_series.dropna().empty else window_df.index[0]
    )
    rotation_peak_index = (
        rotation_series.idxmax()
        if not rotation_series.dropna().empty
        else window_df.index[0]
    )
    wrist_peak_row = df.loc[wrist_peak_index]
    rotation_peak_row = df.loc[rotation_peak_index]

    wrist_speed_peak = safe_float(wrist_peak_row["throwing_wrist_speed"], 0.0)
    rotation_activity_peak = safe_float(rotation_peak_row["rotation_activity"], 0.0)
    wrist_speed_peak_time = safe_float(wrist_peak_row["time_seconds"], candidate_time)
    rotation_activity_peak_time = safe_float(rotation_peak_row["time_seconds"], candidate_time)
    mean_visibility = safe_float(window_df["visibility_score"].mean(), 0.0)
    row = df.iloc[candidate["position"]]
    visibility_at_peak = safe_float(row["visibility_score"], 0.0)

    normalized_wrist_peak = normalized_peak(
        wrist_speed_peak, median_wrist_speed, high_wrist_speed
    )
    normalized_rotation_peak = normalized_peak(
        rotation_activity_peak, median_rotation_activity, high_rotation_activity
    )
    if wrist_speed_peak > 0:
        wrist_burst_clarity = (wrist_speed_peak - median_wrist_speed) / wrist_speed_peak
    else:
        wrist_burst_clarity = 0.0
    wrist_burst_clarity = float(np.clip(wrist_burst_clarity, 0.0, 1.0))

    pitch_likeness_score = (
        (normalized_wrist_peak * 0.4)
        + (normalized_rotation_peak * 0.3)
        + (mean_visibility * 0.2)
        + (wrist_burst_clarity * 0.1)
    )

    lead_stability = lead_ankle_stability_score(
        window_df, fps, candidate_time, throwing_hand
    )
    has_clear_wrist_acceleration = (
        wrist_speed_peak >= median_wrist_speed * 1.35
        and wrist_burst_clarity >= 0.25
        and normalized_wrist_peak >= 0.20
    )
    has_rotation_activity = (
        rotation_activity_peak >= median_rotation_activity * 1.25
        and normalized_rotation_peak >= 0.20
    )
    enough_motion_before_peak = candidate_time - start_time >= 0.5
    enough_frames_after_peak = end_time - candidate_time >= 0.25
    not_near_video_edge = candidate_time >= 0.5 and candidate_time <= duration_seconds - 0.5

    rejection_reasons = []
    if mean_visibility < 0.5:
        rejection_reasons.append("poor visibility")
    if wrist_speed_peak < median_wrist_speed * 1.35 or normalized_wrist_peak < 0.20:
        rejection_reasons.append("weak wrist burst")
    if rotation_activity_peak < median_rotation_activity * 1.25 or normalized_rotation_peak < 0.20:
        rejection_reasons.append("weak rotation")
    if not not_near_video_edge:
        rejection_reasons.append("too close to video edge")
    if not enough_motion_before_peak:
        rejection_reasons.append("not enough motion before peak")
    if not enough_frames_after_peak:
        rejection_reasons.append("not enough frames after peak")
    if pitch_likeness_score < min_pitch_likeness:
        rejection_reasons.append("low pitch_likeness")
    if normalized_wrist_peak >= 0.45 and normalized_rotation_peak < 0.20:
        rejection_reasons.append("high wrist speed but low rotation")
    if normalized_rotation_peak >= 0.45 and normalized_wrist_peak < 0.20:
        rejection_reasons.append("high rotation but low wrist speed")

    validation_passed = len(rejection_reasons) == 0
    confidence = confidence_for_candidate(
        pitch_likeness_score,
        max(min_pitch_likeness, median_score),
        mean_visibility,
    )

    return {
        "frame": candidate_peak_frame,
        "candidate_peak_frame": candidate_peak_frame,
        "candidate_peak_time": candidate_time,
        "start_time": start_time,
        "end_time": end_time,
        "score": candidate["score"],
        "activity_score": candidate["score"],
        "wrist_speed_at_peak": safe_float(row["throwing_wrist_speed"], 0.0),
        "rotation_activity_at_peak": safe_float(row["rotation_activity"], 0.0),
        "visibility_at_peak": visibility_at_peak,
        "wrist_speed_peak": wrist_speed_peak,
        "wrist_speed_peak_time": wrist_speed_peak_time,
        "rotation_activity_peak": rotation_activity_peak,
        "rotation_activity_peak_time": rotation_activity_peak_time,
        "mean_visibility": mean_visibility,
        "lead_ankle_stability_after_peak": lead_stability,
        "has_clear_wrist_acceleration": bool(has_clear_wrist_acceleration),
        "has_rotation_activity": bool(has_rotation_activity),
        "estimated_release_time": wrist_speed_peak_time,
        "estimated_ffs_time": max(start_time, candidate_time - 0.35),
        "normalized_wrist_peak": normalized_wrist_peak,
        "normalized_rotation_peak": normalized_rotation_peak,
        "wrist_burst_clarity": wrist_burst_clarity,
        "pitch_likeness_score": float(pitch_likeness_score),
        "validation_passed": bool(validation_passed),
        "rejection_reason": " / ".join(rejection_reasons) if rejection_reasons else "",
        "confidence": confidence,
        "debug_reason": (
            f"activity_score={candidate['score']:.3f}, pitch_likeness={pitch_likeness_score:.3f}, "
            f"wrist_peak={wrist_speed_peak:.3f}, rotation_peak={rotation_activity_peak:.3f}, "
            f"mean_visibility={mean_visibility:.3f}, wrist_burst={wrist_burst_clarity:.3f}"
        ),
    }


def find_candidate_peaks(
    df,
    fps,
    max_windows,
    duration_seconds,
    throwing_hand,
    min_pitch_likeness,
    max_overlap_ratio,
):
    """Find high-activity peaks, validate them, and select pitch-like windows."""
    median_score = safe_float(df["pitch_activity_score"].median(), 0.0)
    median_wrist_speed = safe_float(df["throwing_wrist_speed"].median(), 0.0)
    high_wrist_speed = safe_float(df["throwing_wrist_speed"].quantile(0.95), 0.0)
    median_rotation_activity = safe_float(df["rotation_activity"].median(), 0.0)
    high_rotation_activity = safe_float(df["rotation_activity"].quantile(0.95), 0.0)

    raw_candidates = generate_activity_candidates(df, fps)
    validated_candidates = [
        validate_candidate_window(
            df,
            candidate,
            fps,
            duration_seconds,
            throwing_hand,
            median_score,
            median_wrist_speed,
            high_wrist_speed,
            median_rotation_activity,
            high_rotation_activity,
            min_pitch_likeness,
        )
        for candidate in raw_candidates
    ]

    sorted_candidates = sorted(
        validated_candidates,
        key=lambda item: item["pitch_likeness_score"],
        reverse=True,
    )

    selected = []
    for candidate in sorted_candidates:
        if len(selected) >= max_windows:
            break
        if not candidate["validation_passed"]:
            continue

        overlapping_window = None
        for selected_window in selected:
            if window_overlap_ratio(candidate, selected_window) > max_overlap_ratio:
                overlapping_window = selected_window
                break

        if overlapping_window:
            candidate["validation_passed"] = False
            candidate["rejection_reason"] = "overlaps selected higher-confidence window"
            continue

        selected.append(candidate)

    for selected_window in selected:
        selected_window.pop("frame", None)

    return selected, validated_candidates


def write_windows_json(output_path, video_path, fps, total_frames, duration, throwing_hand, windows):
    """Write detected windows to JSON."""
    report = {
        "video_path": str(video_path),
        "fps": fps,
        "total_frames": total_frames,
        "duration_seconds": duration,
        "throwing_hand": throwing_hand,
        "windows": windows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def write_debug_candidates_csv(output_path, candidates):
    """Write candidate validation details for debugging false positives."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not candidates:
        pd.DataFrame().to_csv(output_path, index=False)
        return

    debug_columns = [
        "candidate_peak_frame",
        "candidate_peak_time",
        "start_time",
        "end_time",
        "activity_score",
        "pitch_likeness_score",
        "wrist_burst_clarity",
        "mean_visibility",
        "wrist_speed_peak",
        "wrist_speed_peak_time",
        "rotation_activity_peak",
        "rotation_activity_peak_time",
        "lead_ankle_stability_after_peak",
        "has_clear_wrist_acceleration",
        "has_rotation_activity",
        "estimated_release_time",
        "estimated_ffs_time",
        "validation_passed",
        "rejection_reason",
    ]
    pd.DataFrame(candidates).to_csv(output_path, columns=debug_columns, index=False)


def run_analysis_for_windows(video_path, throwing_hand, output_prefix, windows):
    """Call analyze_pitch_timing.py for each detected window."""
    for window in windows:
        window_prefix = f"{output_prefix}_window_{window['window_id']}"
        command = [
            sys.executable,
            "analyze_pitch_timing.py",
            str(video_path),
            "--throwing-hand",
            throwing_hand,
            "--start-time",
            f"{window['start_time']:.3f}",
            "--end-time",
            f"{window['end_time']:.3f}",
            "--peak-search-start-ms",
            "0",
            "--pelvis-peak-search-end-ms",
            "250",
            "--trunk-peak-search-end-ms",
            "300",
            "--ball-release-search-start-ms",
            "30",
            "--ball-release-search-end-ms",
            "250",
            "--output-prefix",
            window_prefix,
        ]
        print(f"Running analysis for window {window['window_id']}...")
        subprocess.run(command, check=True)


def main():
    """CLI entry point."""
    args = parse_args()
    video_path = Path(args.video_path)
    output_dir = Path(args.output_dir)

    fps, total_frames, duration_seconds = video_metadata(video_path)
    df = extract_pose_landmarks(video_path, fps, total_frames)
    df = add_activity_signals(df, fps, args.throwing_hand)

    windows, validated_candidates = find_candidate_peaks(
        df,
        fps,
        max(1, args.max_windows),
        duration_seconds,
        args.throwing_hand,
        args.min_pitch_likeness,
        args.max_overlap_ratio,
    )
    for index, window in enumerate(windows, start=1):
        window["window_id"] = index

    output_path = output_dir / f"{args.output_prefix}_pitch_windows.json"
    write_windows_json(
        output_path,
        video_path,
        fps,
        total_frames,
        duration_seconds,
        args.throwing_hand,
        windows,
    )

    if args.debug_candidates:
        debug_path = output_dir / f"{args.output_prefix}_pitch_window_candidates.csv"
        write_debug_candidates_csv(debug_path, validated_candidates)
        print(f"Saved candidate debug CSV: {debug_path}")

    print("\nSelected pitch windows:")
    if not windows:
        print("No valid pitch-like windows detected after second-stage validation.")
    for window in windows:
        print(
            f"window {window['window_id']}: "
            f"start={window['start_time']:.2f}s "
            f"end={window['end_time']:.2f}s "
            f"peak={window['candidate_peak_time']:.2f}s "
            f"pitch_likeness={window['pitch_likeness_score']:.3f} "
            f"confidence={window['confidence']}"
        )

    rejected_candidates = [
        candidate
        for candidate in validated_candidates
        if not candidate["validation_passed"] and candidate["rejection_reason"]
    ]
    rejected_candidates = sorted(
        rejected_candidates,
        key=lambda item: item["activity_score"],
        reverse=True,
    )
    print("\nRejected high-activity candidates:")
    if not rejected_candidates:
        print("No high-activity candidates were rejected.")
    for candidate in rejected_candidates[:8]:
        print(
            f"time={candidate['candidate_peak_time']:.2f}s "
            f"activity={candidate['activity_score']:.3f} "
            f"pitch_likeness={candidate['pitch_likeness_score']:.3f} "
            f"reason={candidate['rejection_reason']}"
        )
    print(f"\nSaved pitch windows: {output_path}")

    if args.run_analysis and windows:
        run_analysis_for_windows(
            video_path,
            args.throwing_hand,
            args.output_prefix,
            windows,
        )


if __name__ == "__main__":
    main()
