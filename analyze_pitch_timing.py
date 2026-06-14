#!/usr/bin/env python3
"""
Minimal local MVP for baseball pitching timing analysis.

This script:
- Reads a local video with OpenCV.
- Optionally trims analysis to a start/end time.
- Runs MediaPipe Pose locally on each processed frame.
- Saves selected pose landmarks to CSV.
- Estimates a few simple pitching timing events.
- Writes a JSON timing report, angle plot, and pose overlay video.

No cloud API is used. No API key is required.
"""

import argparse
import json
import math
from pathlib import Path

import cv2
import matplotlib

# Use a non-interactive backend so plotting works in terminals and scripts.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
]

EVENT_SPECS = [
    ("front_foot_strike_frame", "FRONT FOOT STRIKE", (0, 255, 0), "front_foot_strike"),
    ("pelvis_peak_frame", "PELVIS PEAK", (0, 165, 255), "pelvis_peak"),
    ("trunk_peak_frame", "TRUNK PEAK", (0, 0, 255), "trunk_peak"),
    ("ball_release_frame", "BALL RELEASE", (255, 0, 255), "ball_release"),
]

OVERLAY_EVENT_SPECS = EVENT_SPECS + [
    (
        "max_hip_shoulder_separation_delivery_window_frame",
        "MAX DELIVERY SEP",
        (255, 255, 0),
        "max_delivery_sep",
    ),
    (
        "max_hip_shoulder_separation_stretch_phase_frame",
        "MAX STRETCH SEP",
        (255, 255, 0),
        "max_sep_stretch",
    ),
    (
        "max_layback_proxy_frame",
        "MAX LAYBACK PROXY",
        (255, 128, 255),
        "max_layback_proxy",
    ),
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze basic pitching timing from a local video."
    )
    parser.add_argument(
        "video_path",
        help="Path to a local pitching video, for example: videos/pitch.mp4",
    )
    parser.add_argument(
        "--throwing-hand",
        choices=["right", "left"],
        required=True,
        help="Pitcher's throwing hand. Used to estimate the lead/front foot.",
    )
    parser.add_argument(
        "--start-time",
        type=float,
        default=None,
        help="Optional start time in seconds. Frames before this time are skipped.",
    )
    parser.add_argument(
        "--end-time",
        type=float,
        default=None,
        help="Optional end time in seconds. Frames at/after this time are skipped.",
    )
    parser.add_argument(
        "--front-foot-strike-frame",
        type=int,
        default=None,
        help="Optional manual original-video frame number for front foot strike.",
    )
    parser.add_argument(
        "--pelvis-peak-frame",
        type=int,
        default=None,
        help="Optional manual original-video frame number for pelvis peak.",
    )
    parser.add_argument(
        "--trunk-peak-frame",
        type=int,
        default=None,
        help="Optional manual original-video frame number for trunk peak.",
    )
    parser.add_argument(
        "--ball-release-frame",
        type=int,
        default=None,
        help="Optional manual original-video frame number for ball release.",
    )
    parser.add_argument(
        "--peak-search-start-ms",
        type=float,
        default=0.0,
        help="Start of pelvis/trunk peak search window after front foot strike, in milliseconds.",
    )
    parser.add_argument(
        "--pelvis-peak-search-end-ms",
        type=float,
        default=300.0,
        help="End of pelvis peak search window after front foot strike, in milliseconds.",
    )
    parser.add_argument(
        "--trunk-peak-search-end-ms",
        type=float,
        default=350.0,
        help="End of trunk peak search window after front foot strike, in milliseconds.",
    )
    parser.add_argument(
        "--ball-release-search-start-ms",
        type=float,
        default=30.0,
        help="Start of ball release search window after trunk peak, in milliseconds.",
    )
    parser.add_argument(
        "--ball-release-search-end-ms",
        type=float,
        default=250.0,
        help="End of ball release search window after trunk peak, in milliseconds.",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs",
        help="Directory for landmarks.csv, timing_report.json, angles_plot.png, and pose_overlay.mp4.",
    )
    parser.add_argument(
        "--output-prefix",
        default=None,
        help="Optional prefix for all output files, for example: bullpen_01.",
    )
    parser.add_argument(
        "--export-event-review",
        action="store_true",
        help="Export JPEG review frames around the selected event frames.",
    )
    parser.add_argument(
        "--export-all-review-frames",
        action="store_true",
        help="Export every 5th processed frame as a JPEG for visual review.",
    )
    parser.add_argument(
        "--smoothing-window",
        type=int,
        default=5,
        help="Moving-average window size in frames for angle smoothing.",
    )
    return parser.parse_args()


def landmark_to_columns(prefix, landmark):
    """Return x, y, and visibility values for one MediaPipe landmark."""
    if landmark is None:
        return {
            f"{prefix}_x": np.nan,
            f"{prefix}_y": np.nan,
            f"{prefix}_visibility": np.nan,
        }

    return {
        f"{prefix}_x": landmark.x,
        f"{prefix}_y": landmark.y,
        f"{prefix}_visibility": landmark.visibility,
    }


def line_angle_degrees(x1, y1, x2, y2):
    """
    Calculate the raw angle, in degrees, of the line from point 1 to point 2.

    The x and y values are MediaPipe's normalized image coordinates.
    """
    if any(pd.isna(value) for value in [x1, y1, x2, y2]):
        return np.nan

    return math.degrees(math.atan2(y2 - y1, x2 - x1))


def joint_angle_degrees(ax, ay, bx, by, cx, cy):
    """Calculate the angle at point B formed by A-B-C in degrees."""
    if any(pd.isna(value) for value in [ax, ay, bx, by, cx, cy]):
        return np.nan

    vector_a = np.array([ax - bx, ay - by], dtype=float)
    vector_c = np.array([cx - bx, cy - by], dtype=float)
    norm_product = np.linalg.norm(vector_a) * np.linalg.norm(vector_c)
    if norm_product == 0:
        return np.nan

    cosine_angle = np.dot(vector_a, vector_c) / norm_product
    cosine_angle = np.clip(cosine_angle, -1.0, 1.0)
    return math.degrees(math.acos(cosine_angle))


def unwrap_angle_series_degrees(angle_series):
    """
    Unwrap an angle series so angular velocity does not spike at -180/180 jumps.

    Steps are intentionally explicit:
    1. Start with raw degrees.
    2. Convert to radians.
    3. Use numpy.unwrap.
    4. Convert back to degrees.
    """
    filled = angle_series.interpolate(limit_direction="both")
    if filled.isna().all():
        return filled

    radians = np.deg2rad(filled.to_numpy())
    unwrapped_radians = np.unwrap(radians)
    return pd.Series(np.rad2deg(unwrapped_radians), index=angle_series.index)


def smooth_series(series, window_size):
    """Smooth a series with a simple centered moving average."""
    window_size = max(1, int(window_size))
    return series.rolling(
        window=window_size,
        center=True,
        min_periods=1,
    ).mean()


def angular_velocity_degrees_per_second(angle_degrees, fps):
    """Calculate angular velocity as frame-to-frame angle change per second."""
    if fps <= 0 or len(angle_degrees) < 2 or angle_degrees.isna().all():
        return pd.Series(np.nan, index=angle_degrees.index)

    # np.gradient gives a simple central-difference style derivative.
    velocity = np.gradient(angle_degrees.to_numpy()) * fps
    return pd.Series(velocity, index=angle_degrees.index)


def signed_shortest_angle_difference_degrees(angle_a, angle_b):
    """Return signed shortest difference angle_a - angle_b in degrees."""
    return (angle_a - angle_b + 180.0) % 360.0 - 180.0


def clamp(value, low=0.0, high=1.0):
    """Clamp a numeric value into a bounded range."""
    if pd.isna(value):
        return low
    return max(low, min(high, float(value)))


def lead_ankle_name(throwing_hand):
    """Return the lead ankle landmark name for the throwing hand."""
    return "left_ankle" if throwing_hand == "right" else "right_ankle"


def throwing_wrist_name(throwing_hand):
    """Return the throwing-side wrist landmark name for the throwing hand."""
    return "right_wrist" if throwing_hand == "right" else "left_wrist"


def throwing_shoulder_name(throwing_hand):
    """Return the throwing-side shoulder landmark name for the throwing hand."""
    return "right_shoulder" if throwing_hand == "right" else "left_shoulder"


def throwing_elbow_name(throwing_hand):
    """Return the throwing-side elbow landmark name for the throwing hand."""
    return "right_elbow" if throwing_hand == "right" else "left_elbow"


def coordinate_velocity(series, fps):
    """Calculate normalized coordinate velocity per second."""
    if fps <= 0 or len(series) < 2 or series.isna().all():
        return pd.Series(np.nan, index=series.index)

    filled = series.astype(float).interpolate(limit_direction="both")
    velocity = np.gradient(filled.to_numpy()) * fps
    return pd.Series(velocity, index=series.index)


def get_video_info(video_path):
    """Open the video long enough to read FPS, frame count, width, and height."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    original_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    if not fps or fps <= 0:
        raise RuntimeError("Could not read a valid FPS value from the video.")
    if original_total_frames <= 0:
        raise RuntimeError("Could not read a valid frame count from the video.")
    if width <= 0 or height <= 0:
        raise RuntimeError("Could not read valid video dimensions.")

    return float(fps), original_total_frames, width, height


def resolve_processing_range(fps, original_total_frames, start_time, end_time):
    """Convert optional start/end times into an original-frame range."""
    video_duration = original_total_frames / fps
    processed_start_time = 0.0 if start_time is None else max(0.0, float(start_time))
    processed_end_time = video_duration if end_time is None else min(video_duration, float(end_time))

    if processed_end_time <= processed_start_time:
        raise ValueError("end-time must be greater than start-time.")

    start_frame = max(0, int(math.floor(processed_start_time * fps)))
    end_frame = min(original_total_frames, int(math.ceil(processed_end_time * fps)))

    if end_frame <= start_frame:
        raise ValueError("The selected time range does not contain any frames.")

    return start_frame, end_frame, processed_start_time, processed_end_time


def add_lead_ankle_debug(df, fps, throwing_hand):
    """Add lead ankle velocity, speed, and stability debug columns."""
    df = df.copy()
    lead_ankle = lead_ankle_name(throwing_hand)
    x = df[f"{lead_ankle}_x"].astype(float)
    y = df[f"{lead_ankle}_y"].astype(float)

    df["lead_ankle_x_velocity"] = coordinate_velocity(x, fps)
    df["lead_ankle_y_velocity"] = coordinate_velocity(y, fps)
    df["lead_ankle_speed"] = np.sqrt(
        df["lead_ankle_x_velocity"] ** 2 + df["lead_ankle_y_velocity"] ** 2
    )

    if x.isna().all() or y.isna().all():
        df["lead_ankle_stability_score"] = np.nan
        return df

    x_filled = x.interpolate(limit_direction="both").to_numpy()
    y_filled = y.interpolate(limit_direction="both").to_numpy()
    speed = df["lead_ankle_speed"].to_numpy()
    stable_frames_required = 5
    stability_scores = []

    for row_position in range(len(df)):
        window_end = min(len(df), row_position + stable_frames_required)
        x_window = x_filled[row_position:window_end]
        y_window = y_filled[row_position:window_end]
        speed_window = speed[row_position:window_end]

        if len(x_window) < 2 or np.isnan(x_window).all() or np.isnan(y_window).all():
            stability_scores.append(np.nan)
            continue

        x_range = np.nanmax(x_window) - np.nanmin(x_window)
        y_range = np.nanmax(y_window) - np.nanmin(y_window)
        position_range = math.hypot(x_range, y_range)
        mean_speed = np.nanmean(speed_window)

        # Normalized image coordinates usually range 0-1. These simple MVP
        # thresholds treat a small future position range and low speed as stable.
        position_score = 1.0 - min(1.0, position_range / 0.05)
        speed_score = 1.0 - min(1.0, mean_speed / 0.75)
        stability_scores.append(clamp((0.65 * position_score) + (0.35 * speed_score)))

    df["lead_ankle_stability_score"] = stability_scores
    return df


def add_throwing_wrist_debug(df, fps, throwing_hand):
    """Add throwing wrist velocity and speed debug columns."""
    df = df.copy()
    wrist = throwing_wrist_name(throwing_hand)
    x = df[f"{wrist}_x"].astype(float)
    y = df[f"{wrist}_y"].astype(float)

    df["throwing_wrist_x_velocity"] = coordinate_velocity(x, fps)
    df["throwing_wrist_y_velocity"] = coordinate_velocity(y, fps)
    df["throwing_wrist_speed"] = np.sqrt(
        df["throwing_wrist_x_velocity"] ** 2 + df["throwing_wrist_y_velocity"] ** 2
    )
    return df


def add_throwing_arm_metrics(df, throwing_hand):
    """Add simple 2D throwing arm angle proxy metrics."""
    df = df.copy()
    shoulder = throwing_shoulder_name(throwing_hand)
    elbow = throwing_elbow_name(throwing_hand)
    wrist = throwing_wrist_name(throwing_hand)

    df["throwing_upper_arm_angle"] = df.apply(
        lambda row: line_angle_degrees(
            row[f"{shoulder}_x"],
            row[f"{shoulder}_y"],
            row[f"{elbow}_x"],
            row[f"{elbow}_y"],
        ),
        axis=1,
    )
    df["throwing_forearm_angle"] = df.apply(
        lambda row: line_angle_degrees(
            row[f"{elbow}_x"],
            row[f"{elbow}_y"],
            row[f"{wrist}_x"],
            row[f"{wrist}_y"],
        ),
        axis=1,
    )
    df["throwing_elbow_angle"] = df.apply(
        lambda row: joint_angle_degrees(
            row[f"{shoulder}_x"],
            row[f"{shoulder}_y"],
            row[f"{elbow}_x"],
            row[f"{elbow}_y"],
            row[f"{wrist}_x"],
            row[f"{wrist}_y"],
        ),
        axis=1,
    )
    df["throwing_arm_visibility"] = df[
        [
            f"{shoulder}_visibility",
            f"{elbow}_visibility",
            f"{wrist}_visibility",
        ]
    ].min(axis=1)
    df["layback_proxy"] = signed_shortest_angle_difference_degrees(
        df["throwing_forearm_angle"],
        df["shoulder_angle_smoothed"],
    )
    df["layback_proxy_abs"] = df["layback_proxy"].abs()
    return df


def safe_percentile(values, percentile, default):
    """Return a percentile from finite values, or a default if none exist."""
    finite_values = np.asarray(values, dtype=float)
    finite_values = finite_values[np.isfinite(finite_values)]
    if len(finite_values) == 0:
        return default
    return float(np.nanpercentile(finite_values, percentile))


def candidate_metric(values, row_position, window_size, mode="mean"):
    """Read a small future or previous metric window safely."""
    window = np.asarray(values[row_position : row_position + window_size], dtype=float)
    window = window[np.isfinite(window)]
    if len(window) == 0:
        return np.nan
    if mode == "max":
        return float(np.nanmax(window))
    return float(np.nanmean(window))


def rotation_increase_score(df, row_position, fps):
    """Score whether hip/shoulder angular velocity rises after a candidate."""
    next_frames = max(1, int(round(0.300 * fps)))
    previous_frames = max(1, int(round(0.100 * fps)))
    rotation = (
        df["hip_angular_velocity"].abs().fillna(0)
        + df["shoulder_angular_velocity"].abs().fillna(0)
    ).to_numpy()

    previous_start = max(0, row_position - previous_frames)
    previous_peak = candidate_metric(rotation, previous_start, row_position - previous_start, "max")
    future_peak = candidate_metric(rotation, row_position, next_frames, "max")

    if pd.isna(previous_peak) or pd.isna(future_peak) or future_peak <= 0:
        return 0.0, 0.0, 0.0

    score = clamp((future_peak - previous_peak) / (future_peak + 1e-6))
    return score, float(previous_peak), float(future_peak)


def build_front_foot_candidate(
    df,
    row_position,
    throwing_hand,
    fps,
    speed_threshold,
    y_stable_threshold,
    downward_threshold,
):
    """Build one candidate score for front foot strike."""
    lead_ankle = lead_ankle_name(throwing_hand)
    stable_frames_required = 5

    speed_values = df["lead_ankle_speed"].to_numpy()
    y_velocity_values = df["lead_ankle_y_velocity"].to_numpy()
    visibility_values = df[f"{lead_ankle}_visibility"].to_numpy()

    future_speed = candidate_metric(speed_values, row_position, stable_frames_required)
    future_y_abs = candidate_metric(
        np.abs(y_velocity_values),
        row_position,
        stable_frames_required,
    )
    previous_start = max(0, row_position - 3)
    previous_y_velocity = candidate_metric(
        y_velocity_values,
        previous_start,
        row_position - previous_start,
    )
    visibility = candidate_metric(visibility_values, row_position, stable_frames_required)
    stability = df.iloc[row_position]["lead_ankle_stability_score"]

    speed_drop_score = clamp((speed_threshold * 1.5 - future_speed) / (speed_threshold * 1.5))
    downward_score = clamp(previous_y_velocity / downward_threshold)
    stable_y_score = clamp((y_stable_threshold * 1.5 - future_y_abs) / (y_stable_threshold * 1.5))
    y_transition_score = (0.55 * stable_y_score) + (0.45 * downward_score)
    rotation_score, previous_rotation_peak, future_rotation_peak = rotation_increase_score(
        df,
        row_position,
        fps,
    )
    visibility_score = clamp(visibility)

    score = (
        (0.30 * clamp(stability))
        + (0.20 * speed_drop_score)
        + (0.20 * y_transition_score)
        + (0.25 * rotation_score)
        + (0.05 * visibility_score)
    )
    score *= 0.40 + (0.60 * visibility_score)
    score = clamp(score)

    rule_matched = (
        clamp(stability) >= 0.45
        and future_speed <= speed_threshold * 1.25
        and downward_score >= 0.15
        and stable_y_score >= 0.35
        and y_transition_score >= 0.35
        and rotation_score >= 0.10
    )

    return {
        "frame": int(df.iloc[row_position]["frame"]),
        "processed_frame": int(df.iloc[row_position]["processed_frame"]),
        "score": round(score, 3),
        "stability_score": round(clamp(stability), 3),
        "speed": round(float(future_speed), 4) if not pd.isna(future_speed) else None,
        "speed_threshold": round(float(speed_threshold), 4),
        "downward_score": round(downward_score, 3),
        "stable_y_score": round(stable_y_score, 3),
        "y_velocity_before": (
            round(float(previous_y_velocity), 4)
            if not pd.isna(previous_y_velocity)
            else None
        ),
        "y_velocity_after_abs": round(float(future_y_abs), 4) if not pd.isna(future_y_abs) else None,
        "rotation_increase_score": round(rotation_score, 3),
        "rotation_peak_before": round(previous_rotation_peak, 3),
        "rotation_peak_after": round(future_rotation_peak, 3),
        "visibility": round(visibility_score, 3),
        "rule_matched": bool(rule_matched),
    }


def detect_front_foot_strike(df, throwing_hand, fps):
    """
    Approximate front foot strike using lead ankle stability plus rotation onset.

    This is still a simple rule-based MVP. It looks for the lead ankle becoming
    stable, lead ankle speed dropping, y velocity settling after downward motion,
    and hip/shoulder angular velocity increasing within the next 300 ms.
    """
    lead_ankle = lead_ankle_name(throwing_hand)
    y = df[f"{lead_ankle}_y"].astype(float)
    if y.isna().all():
        return {
            "frame": None,
            "confidence": 0.0,
            "candidates": [],
            "reason": "No lead ankle landmarks were detected.",
        }

    speed = df["lead_ankle_speed"].to_numpy()
    y_velocity = df["lead_ankle_y_velocity"].to_numpy()
    abs_y_velocity = np.abs(y_velocity)

    speed_threshold = max(0.20, safe_percentile(speed, 35, 0.35))
    y_stable_threshold = max(0.08, safe_percentile(abs_y_velocity, 35, 0.15))
    downward_threshold = max(0.10, safe_percentile(y_velocity[y_velocity > 0], 50, 0.20))

    scored_candidates = []
    for row_position in range(1, max(1, len(df) - 4)):
        candidate = build_front_foot_candidate(
            df,
            row_position,
            throwing_hand,
            fps,
            speed_threshold,
            y_stable_threshold,
            downward_threshold,
        )
        scored_candidates.append(candidate)

    if not scored_candidates:
        return {
            "frame": None,
            "confidence": 0.0,
            "candidates": [],
            "reason": "Not enough processed frames to score front foot strike.",
        }

    rule_matches = [candidate for candidate in scored_candidates if candidate["rule_matched"]]
    candidates_to_rank = rule_matches if rule_matches else scored_candidates
    candidates_to_rank = sorted(candidates_to_rank, key=lambda item: item["score"], reverse=True)
    best_score_candidate = candidates_to_rank[0]
    best_score = best_score_candidate["score"]
    similar_candidates = [
        candidate
        for candidate in candidates_to_rank
        if best_score - candidate["score"] <= 0.05
    ]
    earliest_reasonable_candidates = [
        candidate
        for candidate in similar_candidates
        if (
            candidate["rule_matched"]
            and candidate["stability_score"] >= 0.85
            and candidate["speed"] is not None
            and candidate["speed_threshold"] is not None
            and candidate["speed"] <= candidate["speed_threshold"]
            and candidate["visibility"] >= 0.80
        )
    ]
    earliest_similar_selection_used = bool(earliest_reasonable_candidates)

    if earliest_similar_selection_used:
        best = sorted(earliest_reasonable_candidates, key=lambda item: item["frame"])[0]
    else:
        best = best_score_candidate

    confidence = best["score"]
    if not best["rule_matched"]:
        confidence = min(confidence, 0.35)
    if len(similar_candidates) > 1:
        confidence -= min(0.25, 0.06 * (len(similar_candidates) - 1))
    if best["visibility"] < 0.60:
        confidence *= 0.75
    confidence = round(clamp(confidence), 3)

    shown_candidates = candidates_to_rank[:8] if rule_matches else candidates_to_rank[:5]
    candidate_type = "rule-matched" if rule_matches else "fallback scored"
    reason = (
        f"Selected frame {best['frame']} from {len(rule_matches)} rule-matched candidates. "
        f"Candidate type: {candidate_type}. "
        f"best_score={best_score}. "
        f"similar_candidates={len(similar_candidates)}. "
        f"earliest_similar_candidate_selection_used={earliest_similar_selection_used}. "
        f"selected_frame={best['frame']}. "
        f"Stability={best['stability_score']}, speed={best['speed']} "
        f"(threshold {best['speed_threshold']}), "
        f"rotation_increase_score={best['rotation_increase_score']}, "
        f"visibility={best['visibility']}."
    )
    if earliest_similar_selection_used:
        reason += " Earliest high-quality similar candidate was selected."
    if len(similar_candidates) > 1:
        reason += f" Confidence reduced because {len(similar_candidates)} candidates had similar scores."
    if best["visibility"] < 0.60:
        reason += " Confidence reduced because lead ankle visibility was low."
    if not best["rule_matched"]:
        reason += " No candidate satisfied every rule, so the best fallback score was used."

    return {
        "frame": int(best["frame"]),
        "confidence": confidence,
        "candidates": shown_candidates,
        "reason": reason,
    }


def peak_search_window_frames(front_foot_strike_frame, fps, start_ms, end_ms):
    """Convert a post-front-foot-strike time window into original frame bounds."""
    if front_foot_strike_frame is None or fps <= 0:
        return None, None
    if end_ms < start_ms:
        raise ValueError("Peak search end time must be greater than or equal to start time.")

    start_offset_frames = int(math.ceil((start_ms / 1000.0) * fps))
    end_offset_frames = int(math.floor((end_ms / 1000.0) * fps))
    return (
        int(front_foot_strike_frame + start_offset_frames),
        int(front_foot_strike_frame + end_offset_frames),
    )


def event_search_window_frames(base_frame, fps, start_ms, end_ms):
    """Convert an event-relative time window into original frame bounds."""
    if base_frame is None or fps <= 0:
        return None, None
    if end_ms < start_ms:
        raise ValueError("Search end time must be greater than or equal to start time.")

    start_offset_frames = int(math.ceil((start_ms / 1000.0) * fps))
    end_offset_frames = int(math.floor((end_ms / 1000.0) * fps))
    return (
        int(base_frame + start_offset_frames),
        int(base_frame + end_offset_frames),
    )


def peak_in_frame_window(df, series_name, start_frame, end_frame):
    """Return the original-video frame with max absolute value inside a frame window."""
    if start_frame is None or end_frame is None:
        return None

    search_df = df[(df["frame"] >= start_frame) & (df["frame"] <= end_frame)]

    search = search_df[["frame", series_name]].dropna()
    if search.empty:
        return None

    peak_index = search[series_name].abs().idxmax()
    return int(search.loc[peak_index, "frame"])


def max_value_frame_in_window(df, series_name, start_frame, end_frame):
    """Return the original-video frame with the maximum value inside a frame window."""
    if start_frame is None or end_frame is None:
        return None

    search_df = df[(df["frame"] >= start_frame) & (df["frame"] <= end_frame)]
    search = search_df[["frame", series_name]].dropna()
    if search.empty:
        return None

    peak_index = search[series_name].idxmax()
    return int(search.loc[peak_index, "frame"])


def value_at_frame(df, frame_number, column_name):
    """Return a dataframe value at an original-video frame, or None."""
    if frame_number is None or column_name not in df.columns:
        return None

    rows = df[df["frame"] == frame_number]
    if rows.empty:
        return None

    value = rows.iloc[0][column_name]
    if pd.isna(value):
        return None
    return float(value)


def max_separation_in_window(df, start_frame, end_frame, fps):
    """Return largest absolute hip-shoulder separation in a frame window."""
    if start_frame is None or end_frame is None:
        return None, None, None, None

    search_df = df[(df["frame"] >= start_frame) & (df["frame"] <= end_frame)]
    search = search_df[["frame", "hip_shoulder_separation"]].dropna()
    if search.empty:
        return None, None, None, None

    max_index = search["hip_shoulder_separation"].abs().idxmax()
    max_value = float(search.loc[max_index, "hip_shoulder_separation"])
    max_abs_value = abs(max_value)
    max_frame = int(search.loc[max_index, "frame"])
    return max_value, max_abs_value, max_frame, frame_to_time(max_frame, fps)


def max_abs_value_in_window(df, column_name, start_frame, end_frame, fps):
    """Return value, absolute value, frame, and time for max absolute column value."""
    if start_frame is None or end_frame is None:
        return None, None, None, None

    search_df = df[(df["frame"] >= start_frame) & (df["frame"] <= end_frame)]
    search = search_df[["frame", column_name]].dropna()
    if search.empty:
        return None, None, None, None

    max_index = search[column_name].abs().idxmax()
    max_value = float(search.loc[max_index, column_name])
    max_abs_value = abs(max_value)
    max_frame = int(search.loc[max_index, "frame"])
    return max_value, max_abs_value, max_frame, frame_to_time(max_frame, fps)


def layback_proxy_window(df, trunk_peak_frame, ball_release_frame, fps):
    """Return the search window for the simple 2D layback proxy."""
    if trunk_peak_frame is None:
        return None, None, True

    search_start_frame = trunk_peak_frame
    if ball_release_frame is not None:
        search_end_frame = ball_release_frame
    else:
        search_end_frame = trunk_peak_frame + int(math.floor(0.250 * fps))

    max_available_frame = int(df["frame"].max()) if not df.empty else search_end_frame
    search_end_frame = min(search_end_frame, max_available_frame)
    if search_end_frame < search_start_frame:
        search_end_frame = search_start_frame

    frame_count = search_end_frame - search_start_frame + 1
    return search_start_frame, search_end_frame, frame_count < 2


def throwing_arm_quality_warning(
    visibility_at_ball_release,
    max_layback_proxy_abs,
    layback_window_too_short,
    ball_release_method,
    ball_release_confidence,
):
    """Return quality warnings for 2D throwing arm proxy interpretation."""
    warnings = []

    if visibility_at_ball_release is not None and visibility_at_ball_release < 0.5:
        warnings.append("Throwing arm visibility at ball release is below 0.5.")

    if max_layback_proxy_abs is not None and max_layback_proxy_abs > 170.0:
        warnings.append(
            "Max 2D layback proxy absolute value is greater than 170 degrees; camera-view angle may be unstable."
        )

    if layback_window_too_short:
        warnings.append("2D layback proxy search window has fewer than 2 frames.")

    if (
        ball_release_method == "auto"
        and ball_release_confidence is not None
        and ball_release_confidence < 0.5
    ):
        warnings.append(
            "Ball release was detected automatically with low confidence; confirm arm proxy values visually."
        )

    if not warnings:
        return "No major 2D throwing arm quality warning."
    return " ".join(warnings)


def delivery_window(front_foot_strike_frame, trunk_peak_frame):
    """Return the delivery-window search range before trunk peak."""
    if front_foot_strike_frame is None:
        return None, None

    if trunk_peak_frame is None:
        return front_foot_strike_frame, front_foot_strike_frame

    delivery_start_frame = front_foot_strike_frame
    delivery_end_frame = trunk_peak_frame - 1
    if delivery_end_frame < delivery_start_frame:
        delivery_end_frame = delivery_start_frame

    return delivery_start_frame, delivery_end_frame


def stretch_phase_window(pelvis_peak_frame, trunk_peak_frame):
    """Return the stretch-phase search window and whether it is very short."""
    if pelvis_peak_frame is None:
        return None, None, True

    if trunk_peak_frame is None:
        return pelvis_peak_frame, pelvis_peak_frame, True

    stretch_start_frame = pelvis_peak_frame
    stretch_end_frame = trunk_peak_frame - 1
    if stretch_end_frame < stretch_start_frame:
        stretch_end_frame = stretch_start_frame

    stretch_frame_count = stretch_end_frame - stretch_start_frame + 1
    return stretch_start_frame, stretch_end_frame, stretch_frame_count < 2


def separation_timing_category(max_frame, pelvis_peak_frame, trunk_peak_frame):
    """Classify when the delivery-window separation max occurred."""
    if max_frame is None or pelvis_peak_frame is None or trunk_peak_frame is None:
        return "unknown"

    if max_frame < pelvis_peak_frame:
        return "before_pelvis_peak_possible_early_trunk_rotation"

    if pelvis_peak_frame <= max_frame < trunk_peak_frame:
        return "between_pelvis_peak_and_trunk_peak"

    return "invalid_at_or_after_trunk_peak"


def separation_timing_interpretation(timing_category):
    """Return plain-English interpretation for separation max timing."""
    if timing_category == "before_pelvis_peak_possible_early_trunk_rotation":
        return (
            "Max 2D separation occurred before pelvis peak. This may indicate "
            "early trunk rotation or sequencing issue, but confirm visually "
            "because this is a 2D proxy."
        )

    if timing_category == "between_pelvis_peak_and_trunk_peak":
        return (
            "Max 2D separation occurred during the expected pelvis-to-trunk "
            "stretch phase."
        )

    if timing_category == "invalid_at_or_after_trunk_peak":
        return (
            "Max separation occurred at or after trunk peak and should not be "
            "interpreted as reliable."
        )

    return "Max 2D separation timing could not be categorized."


def separation_quality_warning(
    df,
    start_frame,
    end_frame,
    max_abs_separation,
    stretch_window_too_short=False,
    timing_category=None,
):
    """Return quality warnings for 2D hip-shoulder separation interpretation."""
    warnings = []

    if stretch_window_too_short:
        warnings.append(
            "Stretch-phase 2D separation window has fewer than 2 frames."
        )

    if max_abs_separation is not None and max_abs_separation > 150.0:
        warnings.append(
            "Max delivery-window absolute 2D separation is greater than 150 degrees; values near +/-180 can be unstable."
        )

    if start_frame is not None and end_frame is not None:
        search_df = df[(df["frame"] >= start_frame) & (df["frame"] <= end_frame)]
        separation = search_df["hip_shoulder_separation"].dropna()
        if len(separation) >= 2:
            max_adjacent_change = float(separation.diff().abs().max())
            if max_adjacent_change > 90.0:
                warnings.append(
                    "Signed 2D separation changes by more than 90 degrees between adjacent frames inside the delivery window."
                )

    if timing_category == "before_pelvis_peak_possible_early_trunk_rotation":
        warnings.append(
            "Max delivery-window 2D separation occurred before pelvis peak; possible early trunk rotation."
        )

    if not warnings:
        return "No major 2D separation quality warning."
    return " ".join(warnings)


def ball_release_confidence_from_peak(
    df,
    throwing_hand,
    selected_frame,
    search_start_frame,
    search_end_frame,
    wrist_speed,
):
    """Estimate confidence for approximate ball release from wrist speed shape."""
    if selected_frame is None or wrist_speed is None:
        return 0.0, "No valid throwing wrist speed peak was found."

    wrist = throwing_wrist_name(throwing_hand)
    visibility = value_at_frame(df, selected_frame, f"{wrist}_visibility")
    visibility_score = clamp(visibility if visibility is not None else 0.0)

    selected_rows = df.index[df["frame"] == selected_frame].tolist()
    if not selected_rows:
        return 0.0, "Selected ball release frame was not present in the processed data."

    row_position = selected_rows[0]
    nearby_start = max(0, row_position - 3)
    nearby_end = min(len(df), row_position + 4)
    nearby = df.iloc[nearby_start:nearby_end]["throwing_wrist_speed"].dropna()
    nearby_without_peak = nearby.drop(index=df.index[row_position], errors="ignore")
    nearby_baseline = float(nearby_without_peak.median()) if not nearby_without_peak.empty else 0.0

    if wrist_speed <= 0:
        peak_clarity_score = 0.0
    else:
        peak_clarity_score = clamp((wrist_speed - nearby_baseline) / wrist_speed)

    first_frame_penalty = 0.25 if selected_frame == search_start_frame else 0.0
    confidence = (
        (0.55 * peak_clarity_score)
        + (0.35 * visibility_score)
        + 0.10
        - first_frame_penalty
    )
    confidence = round(clamp(confidence), 3)

    reason = (
        f"Selected frame {selected_frame} from ball release search window "
        f"{search_start_frame}-{search_end_frame}. "
        f"wrist_speed={wrist_speed:.4f}. "
        f"nearby_median_speed={nearby_baseline:.4f}. "
        f"peak_clarity_score={peak_clarity_score:.3f}. "
        f"visibility={visibility_score:.3f}. "
        f"selected_at_first_search_frame={selected_frame == search_start_frame}."
    )
    if selected_frame == search_start_frame:
        reason += " Confidence reduced because the peak was at the first frame of the search window."
    if peak_clarity_score < 0.35:
        reason += " Confidence reduced because the wrist speed peak was not clearly above nearby frames."
    if visibility_score < 0.60:
        reason += " Confidence reduced because throwing wrist visibility was low."

    return confidence, reason


def detect_ball_release(
    df,
    throwing_hand,
    trunk_peak_frame,
    fps,
    search_start_ms,
    search_end_ms,
):
    """Approximate ball release as max throwing wrist speed after trunk peak."""
    search_start_frame, search_end_frame = event_search_window_frames(
        trunk_peak_frame,
        fps,
        search_start_ms,
        search_end_ms,
    )
    auto_frame = max_value_frame_in_window(
        df,
        "throwing_wrist_speed",
        search_start_frame,
        search_end_frame,
    )
    retry_used = False

    if auto_frame is not None and trunk_peak_frame is not None and auto_frame == trunk_peak_frame:
        retry_used = True
        retry_start_frame = trunk_peak_frame + 2
        if search_start_frame is None:
            search_start_frame = retry_start_frame
        else:
            search_start_frame = max(search_start_frame, retry_start_frame)
        auto_frame = max_value_frame_in_window(
            df,
            "throwing_wrist_speed",
            search_start_frame,
            search_end_frame,
        )

    wrist_speed = value_at_frame(df, auto_frame, "throwing_wrist_speed")
    confidence, reason = ball_release_confidence_from_peak(
        df,
        throwing_hand,
        auto_frame,
        search_start_frame,
        search_end_frame,
        wrist_speed,
    )
    if retry_used:
        reason += " Initial auto release matched trunk peak, so search start was moved at least 2 frames later and retried."

    return {
        "frame": auto_frame,
        "confidence": confidence,
        "reason": reason,
        "wrist_speed": wrist_speed,
        "search_start_frame": search_start_frame,
        "search_end_frame": search_end_frame,
    }


def sequence_message(front_foot_strike_frame, pelvis_peak_frame, trunk_peak_frame):
    """Summarize the basic pelvis/trunk sequence."""
    if (
        front_foot_strike_frame is not None
        and pelvis_peak_frame is not None
        and trunk_peak_frame is not None
        and front_foot_strike_frame < pelvis_peak_frame < trunk_peak_frame
    ):
        return "Basic sequence looks correct: front foot strike -> pelvis -> trunk."

    if (
        trunk_peak_frame is not None
        and pelvis_peak_frame is not None
        and trunk_peak_frame < pelvis_peak_frame
    ):
        return "Possible early trunk rotation: trunk peaks before pelvis."

    return "Sequence unclear. Video angle or landmark quality may be poor."


def frame_to_time(frame_number, fps):
    """Convert an original-video frame number to seconds."""
    if frame_number is None or fps <= 0:
        return None
    return frame_number / fps


def milliseconds_between(later_frame, earlier_frame, fps):
    """Calculate elapsed milliseconds between two original-video frame numbers."""
    if later_frame is None or earlier_frame is None or fps <= 0:
        return None
    return ((later_frame - earlier_frame) / fps) * 1000.0


def extract_landmarks(video_path, fps, start_frame, end_frame):
    """Read the selected video frames and extract selected MediaPipe landmarks."""
    mp_pose = mp.solutions.pose
    pose_landmarks = mp_pose.PoseLandmark

    landmark_indices = {
        "left_shoulder": pose_landmarks.LEFT_SHOULDER.value,
        "right_shoulder": pose_landmarks.RIGHT_SHOULDER.value,
        "left_hip": pose_landmarks.LEFT_HIP.value,
        "right_hip": pose_landmarks.RIGHT_HIP.value,
        "left_ankle": pose_landmarks.LEFT_ANKLE.value,
        "right_ankle": pose_landmarks.RIGHT_ANKLE.value,
        "left_elbow": pose_landmarks.LEFT_ELBOW.value,
        "right_elbow": pose_landmarks.RIGHT_ELBOW.value,
        "left_wrist": pose_landmarks.LEFT_WRIST.value,
        "right_wrist": pose_landmarks.RIGHT_WRIST.value,
    }

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    rows = []
    processed_frame = 0
    total_to_process = end_frame - start_frame
    detected_pose_frames = 0

    print(f"Total frames to process: {total_to_process}")

    # MediaPipe Pose runs locally in this Python process.
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for frame in range(start_frame, end_frame):
            success, frame_bgr = cap.read()
            if not success:
                break

            # MediaPipe expects RGB frames. OpenCV reads BGR frames.
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)

            row = {
                "processed_frame": processed_frame,
                "frame": frame,
                "time_seconds": frame / fps,
                "processed_time_seconds": processed_frame / fps,
                "pose_detected": bool(results.pose_landmarks),
            }

            if results.pose_landmarks:
                detected_pose_frames += 1
                landmarks = results.pose_landmarks.landmark
                for name in LANDMARK_NAMES:
                    row.update(landmark_to_columns(name, landmarks[landmark_indices[name]]))
            else:
                # Keep one CSV row per processed frame, even if pose detection fails.
                for name in LANDMARK_NAMES:
                    row.update(landmark_to_columns(name, None))

            rows.append(row)
            processed_frame += 1

            if processed_frame % 30 == 0:
                print(f"Processed {processed_frame}/{total_to_process} frames")

    cap.release()

    if processed_frame and processed_frame % 30 != 0:
        print(f"Processed {processed_frame}/{total_to_process} frames")

    landmark_detection_rate = detected_pose_frames / processed_frame if processed_frame else 0.0
    return pd.DataFrame(rows), landmark_detection_rate


def add_calculations(df, fps, smoothing_window, throwing_hand):
    """Add raw angles, unwrapped angles, smoothed angles, and velocities."""
    df = df.copy()

    df["shoulder_angle_raw"] = df.apply(
        lambda row: line_angle_degrees(
            row["left_shoulder_x"],
            row["left_shoulder_y"],
            row["right_shoulder_x"],
            row["right_shoulder_y"],
        ),
        axis=1,
    )

    df["hip_angle_raw"] = df.apply(
        lambda row: line_angle_degrees(
            row["left_hip_x"],
            row["left_hip_y"],
            row["right_hip_x"],
            row["right_hip_y"],
        ),
        axis=1,
    )

    df["shoulder_angle_unwrapped"] = unwrap_angle_series_degrees(df["shoulder_angle_raw"])
    df["hip_angle_unwrapped"] = unwrap_angle_series_degrees(df["hip_angle_raw"])

    # Backward-friendly names now refer to the unwrapped angles used downstream.
    df["shoulder_angle"] = df["shoulder_angle_unwrapped"]
    df["hip_angle"] = df["hip_angle_unwrapped"]

    df["shoulder_angle_smoothed"] = smooth_series(
        df["shoulder_angle_unwrapped"], smoothing_window
    )
    df["hip_angle_smoothed"] = smooth_series(df["hip_angle_unwrapped"], smoothing_window)
    df["hip_shoulder_separation"] = signed_shortest_angle_difference_degrees(
        df["shoulder_angle_smoothed"],
        df["hip_angle_smoothed"],
    )
    df["hip_shoulder_separation_abs"] = df["hip_shoulder_separation"].abs()

    df["shoulder_angular_velocity"] = angular_velocity_degrees_per_second(
        df["shoulder_angle_smoothed"], fps
    )
    df["hip_angular_velocity"] = angular_velocity_degrees_per_second(
        df["hip_angle_smoothed"], fps
    )

    df = add_lead_ankle_debug(df, fps, throwing_hand)
    df = add_throwing_wrist_debug(df, fps, throwing_hand)
    df = add_throwing_arm_metrics(df, throwing_hand)
    return df


def choose_event(manual_frame, auto_frame):
    """Return the selected event frame and whether it was manual or auto."""
    if manual_frame is not None:
        return int(manual_frame), "manual"
    return auto_frame, "auto"


def build_timing_report(
    df,
    fps,
    original_total_frames,
    processed_start_time,
    processed_end_time,
    landmark_detection_rate,
    throwing_hand,
    manual_front_foot_strike_frame,
    manual_pelvis_peak_frame,
    manual_trunk_peak_frame,
    manual_ball_release_frame,
    peak_search_start_ms,
    pelvis_peak_search_end_ms,
    trunk_peak_search_end_ms,
    ball_release_search_start_ms,
    ball_release_search_end_ms,
):
    """Detect or accept event frames and build the JSON-ready timing report."""
    auto_front_foot_strike = detect_front_foot_strike(df, throwing_hand, fps)
    auto_front_foot_strike_frame = auto_front_foot_strike["frame"]
    front_foot_strike_frame, front_foot_method = choose_event(
        manual_front_foot_strike_frame, auto_front_foot_strike_frame
    )

    if manual_front_foot_strike_frame is not None:
        front_foot_strike_confidence = 1.0
        front_foot_strike_debug_reason = (
            f"Manual override used for front foot strike. "
            f"Auto detection suggested frame {auto_front_foot_strike_frame} "
            f"with confidence {auto_front_foot_strike['confidence']}. "
            f"Auto reason: {auto_front_foot_strike['reason']}"
        )
    else:
        front_foot_strike_confidence = auto_front_foot_strike["confidence"]
        front_foot_strike_debug_reason = auto_front_foot_strike["reason"]

    pelvis_search_start_frame, pelvis_search_end_frame = peak_search_window_frames(
        front_foot_strike_frame,
        fps,
        peak_search_start_ms,
        pelvis_peak_search_end_ms,
    )
    trunk_search_start_frame, trunk_search_end_frame = peak_search_window_frames(
        front_foot_strike_frame,
        fps,
        peak_search_start_ms,
        trunk_peak_search_end_ms,
    )

    auto_pelvis_peak_frame = peak_in_frame_window(
        df,
        "hip_angular_velocity",
        pelvis_search_start_frame,
        pelvis_search_end_frame,
    )
    pelvis_peak_frame, pelvis_method = choose_event(
        manual_pelvis_peak_frame, auto_pelvis_peak_frame
    )

    auto_trunk_peak_frame = peak_in_frame_window(
        df,
        "shoulder_angular_velocity",
        trunk_search_start_frame,
        trunk_search_end_frame,
    )
    trunk_peak_frame, trunk_method = choose_event(
        manual_trunk_peak_frame, auto_trunk_peak_frame
    )

    auto_ball_release = detect_ball_release(
        df,
        throwing_hand,
        trunk_peak_frame,
        fps,
        ball_release_search_start_ms,
        ball_release_search_end_ms,
    )
    auto_ball_release_frame = auto_ball_release["frame"]
    ball_release_frame, ball_release_method = choose_event(
        manual_ball_release_frame,
        auto_ball_release_frame,
    )
    ball_release_wrist_speed = value_at_frame(
        df,
        ball_release_frame,
        "throwing_wrist_speed",
    )

    if manual_ball_release_frame is not None:
        ball_release_confidence = 1.0
        ball_release_debug_reason = (
            f"Manual override used for ball release. "
            f"Auto detection suggested frame {auto_ball_release_frame} "
            f"with confidence {auto_ball_release['confidence']}. "
            f"Auto reason: {auto_ball_release['reason']}"
        )
    else:
        ball_release_confidence = auto_ball_release["confidence"]
        ball_release_debug_reason = auto_ball_release["reason"]

    (
        layback_search_start_frame,
        layback_search_end_frame,
        layback_window_too_short,
    ) = layback_proxy_window(df, trunk_peak_frame, ball_release_frame, fps)
    (
        max_layback_proxy,
        max_layback_proxy_abs,
        max_layback_proxy_frame,
        max_layback_proxy_time,
    ) = max_abs_value_in_window(
        df,
        "layback_proxy",
        layback_search_start_frame,
        layback_search_end_frame,
        fps,
    )
    throwing_arm_visibility_at_ball_release = value_at_frame(
        df,
        ball_release_frame,
        "throwing_arm_visibility",
    )
    throwing_arm_warning = throwing_arm_quality_warning(
        throwing_arm_visibility_at_ball_release,
        max_layback_proxy_abs,
        layback_window_too_short,
        ball_release_method,
        ball_release_confidence,
    )

    delivery_start_frame, delivery_end_frame = delivery_window(
        front_foot_strike_frame,
        trunk_peak_frame,
    )
    (
        max_hip_shoulder_separation_delivery_window,
        max_hip_shoulder_separation_abs_delivery_window,
        max_hip_shoulder_separation_delivery_window_frame,
        max_hip_shoulder_separation_delivery_window_time,
    ) = max_separation_in_window(
        df,
        delivery_start_frame,
        delivery_end_frame,
        fps,
    )
    (
        stretch_start_frame,
        stretch_end_frame,
        stretch_window_too_short,
    ) = stretch_phase_window(pelvis_peak_frame, trunk_peak_frame)
    (
        max_hip_shoulder_separation_stretch_phase,
        max_hip_shoulder_separation_abs_stretch_phase,
        max_hip_shoulder_separation_stretch_phase_frame,
        max_hip_shoulder_separation_stretch_phase_time,
    ) = max_separation_in_window(
        df,
        stretch_start_frame,
        stretch_end_frame,
        fps,
    )
    max_hip_shoulder_separation_timing_category = separation_timing_category(
        max_hip_shoulder_separation_delivery_window_frame,
        pelvis_peak_frame,
        trunk_peak_frame,
    )
    hip_shoulder_separation_timing_interpretation = (
        separation_timing_interpretation(
            max_hip_shoulder_separation_timing_category
        )
    )
    hip_shoulder_separation_quality_warning = separation_quality_warning(
        df,
        delivery_start_frame,
        delivery_end_frame,
        max_hip_shoulder_separation_abs_delivery_window,
        stretch_window_too_short,
        max_hip_shoulder_separation_timing_category,
    )

    return {
        "fps": fps,
        "original_total_frames": int(original_total_frames),
        "processed_start_time": processed_start_time,
        "processed_end_time": processed_end_time,
        "processed_frame_count": int(len(df)),
        "peak_search_start_ms": peak_search_start_ms,
        "pelvis_peak_search_end_ms": pelvis_peak_search_end_ms,
        "trunk_peak_search_end_ms": trunk_peak_search_end_ms,
        "ball_release_search_start_ms": ball_release_search_start_ms,
        "ball_release_search_end_ms": ball_release_search_end_ms,
        "pelvis_peak_search_start_frame": pelvis_search_start_frame,
        "pelvis_peak_search_end_frame": pelvis_search_end_frame,
        "trunk_peak_search_start_frame": trunk_search_start_frame,
        "trunk_peak_search_end_frame": trunk_search_end_frame,
        "ball_release_search_start_frame": auto_ball_release["search_start_frame"],
        "ball_release_search_end_frame": auto_ball_release["search_end_frame"],
        "front_foot_strike_confidence": front_foot_strike_confidence,
        "front_foot_strike_auto_candidates": auto_front_foot_strike["candidates"],
        "front_foot_strike_debug_reason": front_foot_strike_debug_reason,
        "front_foot_strike_frame": front_foot_strike_frame,
        "pelvis_peak_frame": pelvis_peak_frame,
        "trunk_peak_frame": trunk_peak_frame,
        "ball_release_frame": ball_release_frame,
        "ball_release_confidence": ball_release_confidence,
        "ball_release_debug_reason": ball_release_debug_reason,
        "ball_release_wrist_speed": ball_release_wrist_speed,
        "upper_arm_angle_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "throwing_upper_arm_angle",
        ),
        "forearm_angle_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "throwing_forearm_angle",
        ),
        "elbow_angle_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "throwing_elbow_angle",
        ),
        "throwing_arm_visibility_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "throwing_arm_visibility",
        ),
        "upper_arm_angle_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "throwing_upper_arm_angle",
        ),
        "forearm_angle_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "throwing_forearm_angle",
        ),
        "elbow_angle_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "throwing_elbow_angle",
        ),
        "throwing_arm_visibility_at_ball_release": (
            throwing_arm_visibility_at_ball_release
        ),
        "arm_slot_angle_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "throwing_forearm_angle",
        ),
        "layback_proxy_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "layback_proxy",
        ),
        "layback_proxy_abs_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "layback_proxy_abs",
        ),
        "layback_proxy_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "layback_proxy",
        ),
        "layback_proxy_abs_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "layback_proxy_abs",
        ),
        "layback_proxy_search_start_frame": layback_search_start_frame,
        "layback_proxy_search_end_frame": layback_search_end_frame,
        "max_layback_proxy_abs": max_layback_proxy_abs,
        "max_layback_proxy": max_layback_proxy,
        "max_layback_proxy_frame": max_layback_proxy_frame,
        "max_layback_proxy_time": max_layback_proxy_time,
        "throwing_arm_quality_warning": throwing_arm_warning,
        "hip_shoulder_separation_at_ffs": value_at_frame(
            df,
            front_foot_strike_frame,
            "hip_shoulder_separation",
        ),
        "hip_shoulder_separation_at_pelvis_peak": value_at_frame(
            df,
            pelvis_peak_frame,
            "hip_shoulder_separation",
        ),
        "hip_shoulder_separation_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "hip_shoulder_separation",
        ),
        "hip_shoulder_separation_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "hip_shoulder_separation",
        ),
        "hip_shoulder_separation_abs_at_ffs": value_at_frame(
            df,
            front_foot_strike_frame,
            "hip_shoulder_separation_abs",
        ),
        "hip_shoulder_separation_abs_at_pelvis_peak": value_at_frame(
            df,
            pelvis_peak_frame,
            "hip_shoulder_separation_abs",
        ),
        "hip_shoulder_separation_abs_at_trunk_peak": value_at_frame(
            df,
            trunk_peak_frame,
            "hip_shoulder_separation_abs",
        ),
        "hip_shoulder_separation_abs_at_ball_release": value_at_frame(
            df,
            ball_release_frame,
            "hip_shoulder_separation_abs",
        ),
        "hip_shoulder_separation_delivery_window_start_frame": delivery_start_frame,
        "hip_shoulder_separation_delivery_window_end_frame": delivery_end_frame,
        "max_hip_shoulder_separation_delivery_window": (
            max_hip_shoulder_separation_delivery_window
        ),
        "max_hip_shoulder_separation_abs_delivery_window": (
            max_hip_shoulder_separation_abs_delivery_window
        ),
        "max_hip_shoulder_separation_delivery_window_frame": (
            max_hip_shoulder_separation_delivery_window_frame
        ),
        "max_hip_shoulder_separation_delivery_window_time": (
            max_hip_shoulder_separation_delivery_window_time
        ),
        "hip_shoulder_separation_stretch_phase_start_frame": stretch_start_frame,
        "hip_shoulder_separation_stretch_phase_end_frame": stretch_end_frame,
        "max_hip_shoulder_separation_stretch_phase": (
            max_hip_shoulder_separation_stretch_phase
        ),
        "max_hip_shoulder_separation_abs_stretch_phase": (
            max_hip_shoulder_separation_abs_stretch_phase
        ),
        "max_hip_shoulder_separation_stretch_phase_frame": (
            max_hip_shoulder_separation_stretch_phase_frame
        ),
        "max_hip_shoulder_separation_stretch_phase_time": (
            max_hip_shoulder_separation_stretch_phase_time
        ),
        "max_hip_shoulder_separation_before_trunk_peak": (
            max_hip_shoulder_separation_stretch_phase
        ),
        "max_hip_shoulder_separation_abs_before_trunk_peak": (
            max_hip_shoulder_separation_abs_stretch_phase
        ),
        "max_hip_shoulder_separation_before_trunk_peak_frame": (
            max_hip_shoulder_separation_stretch_phase_frame
        ),
        "max_hip_shoulder_separation_before_trunk_peak_time": (
            max_hip_shoulder_separation_stretch_phase_time
        ),
        "max_hip_shoulder_separation": max_hip_shoulder_separation_stretch_phase,
        "max_hip_shoulder_separation_abs": (
            max_hip_shoulder_separation_abs_stretch_phase
        ),
        "max_hip_shoulder_separation_frame": (
            max_hip_shoulder_separation_stretch_phase_frame
        ),
        "max_hip_shoulder_separation_time": (
            max_hip_shoulder_separation_stretch_phase_time
        ),
        "max_hip_shoulder_separation_timing_category": (
            max_hip_shoulder_separation_timing_category
        ),
        "hip_shoulder_separation_timing_interpretation": (
            hip_shoulder_separation_timing_interpretation
        ),
        "hip_shoulder_separation_quality_warning": hip_shoulder_separation_quality_warning,
        "front_foot_strike_detection_method": front_foot_method,
        "pelvis_peak_detection_method": pelvis_method,
        "trunk_peak_detection_method": trunk_method,
        "ball_release_detection_method": ball_release_method,
        "front_foot_strike_time": frame_to_time(front_foot_strike_frame, fps),
        "pelvis_peak_time": frame_to_time(pelvis_peak_frame, fps),
        "trunk_peak_time": frame_to_time(trunk_peak_frame, fps),
        "ball_release_time": frame_to_time(ball_release_frame, fps),
        "trunk_to_ball_release_ms": milliseconds_between(
            ball_release_frame,
            trunk_peak_frame,
            fps,
        ),
        "ffs_to_ball_release_ms": milliseconds_between(
            ball_release_frame,
            front_foot_strike_frame,
            fps,
        ),
        "sequence_result": sequence_message(
            front_foot_strike_frame,
            pelvis_peak_frame,
            trunk_peak_frame,
        ),
        "landmark_detection_rate": landmark_detection_rate,
    }


def write_timing_report(report, output_path):
    """Write the JSON timing report."""
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


def write_angles_plot(df, report, output_path):
    """Save a plot of smoothed hip and shoulder angles with event markers."""
    plt.figure(figsize=(12, 6))
    plt.plot(df["frame"], df["hip_angle_smoothed"], label="Hip angle")
    plt.plot(df["frame"], df["shoulder_angle_smoothed"], label="Shoulder angle")
    plt.plot(
        df["frame"],
        df["hip_shoulder_separation"],
        label="Hip-shoulder separation 2D proxy (signed)",
        linestyle=":",
        linewidth=2,
    )
    plt.plot(
        df["frame"],
        df["hip_shoulder_separation_abs"],
        label="Hip-shoulder separation 2D proxy (absolute)",
        linestyle="-.",
        linewidth=1.5,
        alpha=0.75,
    )
    plt.plot(
        df["frame"],
        df["throwing_elbow_angle"],
        label="Throwing elbow angle 2D proxy",
        linestyle="--",
        linewidth=1.4,
        alpha=0.8,
    )
    plt.plot(
        df["frame"],
        df["layback_proxy_abs"],
        label="Layback proxy absolute",
        linestyle=(0, (3, 1, 1, 1)),
        linewidth=1.4,
        alpha=0.8,
    )

    pelvis_window_start = report.get("pelvis_peak_search_start_frame")
    pelvis_window_end = report.get("pelvis_peak_search_end_frame")
    if pelvis_window_start is not None and pelvis_window_end is not None:
        plt.axvspan(
            pelvis_window_start,
            pelvis_window_end,
            color="orange",
            alpha=0.12,
            label="Pelvis peak search window",
        )

    trunk_window_start = report.get("trunk_peak_search_start_frame")
    trunk_window_end = report.get("trunk_peak_search_end_frame")
    if trunk_window_start is not None and trunk_window_end is not None:
        plt.axvspan(
            trunk_window_start,
            trunk_window_end,
            color="red",
            alpha=0.08,
            label="Trunk peak search window",
        )

    event_lines = [
        ("front_foot_strike_frame", "Front foot strike", "green"),
        ("pelvis_peak_frame", "Pelvis peak", "orange"),
        ("trunk_peak_frame", "Trunk peak", "red"),
        ("ball_release_frame", "Ball release", "magenta"),
    ]

    for report_key, label, color in event_lines:
        frame_number = report.get(report_key)
        if frame_number is not None:
            plt.axvline(frame_number, color=color, linestyle="--", label=label)

    plt.xlabel("Frame number")
    plt.ylabel("Angle in degrees")
    plt.title("Pitching Timing Angles")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()


def draw_frame_metadata(frame_bgr, original_frame, start_frame, fps):
    """Draw original frame, processed frame, and timestamp on an image."""
    processed_frame = original_frame - start_frame
    lines = [
        f"Original frame: {original_frame}",
        f"Processed frame: {processed_frame}",
        f"Timestamp: {original_frame / fps:.3f}s",
    ]

    y = 35
    for line in lines:
        cv2.putText(
            frame_bgr,
            line,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        y += 30


def format_degrees(value):
    """Format an optional angle value for overlay text."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.1f} deg"


def format_decimal(value):
    """Format an optional decimal metric for overlay text."""
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}"


def draw_angle_metadata(frame_bgr, original_frame, report, angle_by_frame):
    """Draw compact source angle and hip-shoulder separation details."""
    values = angle_by_frame.get(original_frame, {})
    pelvis_angle = values.get("hip_angle_smoothed")
    shoulder_angle = values.get("shoulder_angle_smoothed")
    signed_sep = values.get("hip_shoulder_separation")
    abs_sep = values.get("hip_shoulder_separation_abs")
    elbow_angle = values.get("throwing_elbow_angle")
    forearm_angle = values.get("throwing_forearm_angle")
    layback_proxy = values.get("layback_proxy")
    arm_visibility = values.get("throwing_arm_visibility")

    lines = [
        f"Pelvis angle: {format_degrees(pelvis_angle)}",
        f"Shoulder/trunk angle: {format_degrees(shoulder_angle)}",
        f"Hip-shoulder sep: {format_degrees(signed_sep)}",
        f"Abs sep: {format_degrees(abs_sep)}",
        f"Elbow angle: {format_degrees(elbow_angle)}",
        f"Forearm angle: {format_degrees(forearm_angle)}",
        f"Layback proxy: {format_degrees(layback_proxy)}",
        f"Arm visibility: {format_decimal(arm_visibility)}",
    ]

    ffs_frame = report.get("front_foot_strike_frame")
    max_delivery_abs_sep = report.get(
        "max_hip_shoulder_separation_abs_delivery_window"
    )
    max_delivery_sep_frame = report.get(
        "max_hip_shoulder_separation_delivery_window_frame"
    )
    if (
        ffs_frame is not None
        and original_frame >= ffs_frame
        and max_delivery_abs_sep is not None
        and max_delivery_sep_frame is not None
    ):
        lines.append(
            f"Max delivery sep: {max_delivery_abs_sep:.1f} deg @ frame {max_delivery_sep_frame}"
        )

    pelvis_peak_frame = report.get("pelvis_peak_frame")
    max_stretch_abs_sep = report.get("max_hip_shoulder_separation_abs_stretch_phase")
    max_stretch_sep_frame = report.get(
        "max_hip_shoulder_separation_stretch_phase_frame"
    )
    if (
        pelvis_peak_frame is not None
        and original_frame >= pelvis_peak_frame
        and max_stretch_abs_sep is not None
        and max_stretch_sep_frame is not None
    ):
        lines.append(
            f"Max stretch sep: {max_stretch_abs_sep:.1f} deg @ frame {max_stretch_sep_frame}"
        )

    trunk_peak_frame = report.get("trunk_peak_frame")
    max_layback_proxy_abs = report.get("max_layback_proxy_abs")
    max_layback_proxy_frame = report.get("max_layback_proxy_frame")
    if (
        trunk_peak_frame is not None
        and original_frame >= trunk_peak_frame
        and max_layback_proxy_abs is not None
        and max_layback_proxy_frame is not None
    ):
        lines.append(
            f"Max layback proxy: {max_layback_proxy_abs:.1f} deg @ frame {max_layback_proxy_frame}"
        )

    warning = report.get("hip_shoulder_separation_quality_warning")
    if warning and warning != "No major 2D separation quality warning.":
        lines.append("2D sep warning: check angle quality")

    arm_warning = report.get("throwing_arm_quality_warning")
    if arm_warning and arm_warning != "No major 2D throwing arm quality warning.":
        lines.append("2D arm warning: check angle quality")

    y = 125
    for line in lines:
        cv2.putText(
            frame_bgr,
            line,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        y += 25


def draw_exact_event_label(frame_bgr, original_frame, report):
    """Draw an event label only on the exact selected event frame."""
    y = 125
    for report_key, label, color, _slug in EVENT_SPECS:
        event_frame = report.get(report_key)
        if event_frame is not None and original_frame == event_frame:
            if report_key == "front_foot_strike_frame":
                confidence = report.get("front_foot_strike_confidence")
                if confidence is not None:
                    label = f"{label} CONF {confidence:.2f}"
            cv2.putText(
                frame_bgr,
                label,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                color,
                2,
                cv2.LINE_AA,
            )
            y += 35


def draw_event_labels(frame_bgr, original_frame, report):
    """Draw event labels for 5 frames starting at each event frame."""
    y = 390
    for report_key, label, color, _slug in OVERLAY_EVENT_SPECS:
        event_frame = report.get(report_key)
        if event_frame is not None and event_frame <= original_frame < event_frame + 5:
            if report_key == "front_foot_strike_frame":
                confidence = report.get("front_foot_strike_confidence")
                if confidence is not None:
                    label = f"{label} CONF {confidence:.2f}"
            cv2.putText(
                frame_bgr,
                label,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.85,
                color,
                2,
                cv2.LINE_AA,
            )
            y += 35


def draw_pose_landmarks(frame_bgr, results, mp_pose, drawing_utils, drawing_styles):
    """Draw MediaPipe pose landmarks on a frame when they are available."""
    if results.pose_landmarks:
        drawing_utils.draw_landmarks(
            frame_bgr,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS,
            landmark_drawing_spec=drawing_styles.get_default_pose_landmarks_style(),
        )


def write_pose_overlay_video(video_path, fps, width, height, start_frame, end_frame, report, df, output_path):
    """Create an MP4 with MediaPipe skeleton, frame/time text, metrics, and event labels."""
    mp_pose = mp.solutions.pose
    drawing_utils = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles
    angle_by_frame = (
        df.set_index("frame")[
            [
                "hip_angle_smoothed",
                "shoulder_angle_smoothed",
                "hip_shoulder_separation",
                "hip_shoulder_separation_abs",
                "throwing_elbow_angle",
                "throwing_forearm_angle",
                "layback_proxy",
                "throwing_arm_visibility",
            ]
        ].to_dict("index")
    )

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open overlay video for writing: {output_path}")

    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for original_frame in range(start_frame, end_frame):
            success, frame_bgr = cap.read()
            if not success:
                break

            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)

            draw_pose_landmarks(frame_bgr, results, mp_pose, drawing_utils, drawing_styles)
            draw_frame_metadata(frame_bgr, original_frame, start_frame, fps)
            draw_angle_metadata(
                frame_bgr,
                original_frame,
                report,
                angle_by_frame,
            )
            draw_event_labels(frame_bgr, original_frame, report)
            writer.write(frame_bgr)

    writer.release()
    cap.release()


def review_dir_path(output_dir, output_prefix, folder_name):
    """Build a review directory path using the optional output prefix."""
    if output_prefix:
        folder_name = f"{output_prefix}_{folder_name}"
    return output_dir / folder_name


def save_review_frame(
    cap,
    pose,
    mp_pose,
    drawing_utils,
    drawing_styles,
    fps,
    start_frame,
    report,
    original_frame,
    output_path,
):
    """Read, annotate, and save one review JPEG."""
    cap.set(cv2.CAP_PROP_POS_FRAMES, original_frame)
    success, frame_bgr = cap.read()
    if not success:
        return False

    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    draw_pose_landmarks(frame_bgr, results, mp_pose, drawing_utils, drawing_styles)
    draw_frame_metadata(frame_bgr, original_frame, start_frame, fps)
    draw_exact_event_label(frame_bgr, original_frame, report)

    return cv2.imwrite(str(output_path), frame_bgr)


def export_event_review_frames(video_path, fps, start_frame, end_frame, report, output_dir):
    """Export JPEG frames from 10 frames before to 10 frames after each event."""
    mp_pose = mp.solutions.pose
    drawing_utils = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles

    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    saved_count = 0
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for report_key, _label, _color, slug in EVENT_SPECS:
            event_frame = report.get(report_key)
            if event_frame is None:
                continue

            window_start = max(start_frame, event_frame - 10)
            window_end = min(end_frame - 1, event_frame + 10)

            for original_frame in range(window_start, window_end + 1):
                offset = original_frame - event_frame
                filename = f"{slug}_frame_{original_frame:06d}_offset_{offset:+03d}.jpg"
                output_path = output_dir / filename
                if save_review_frame(
                    cap,
                    pose,
                    mp_pose,
                    drawing_utils,
                    drawing_styles,
                    fps,
                    start_frame,
                    report,
                    original_frame,
                    output_path,
                ):
                    saved_count += 1

    cap.release()
    print(f"Saved event review frames: {output_dir} ({saved_count} images)")


def export_all_review_frames(video_path, fps, start_frame, end_frame, report, output_dir):
    """Export every 5th processed frame as an annotated JPEG."""
    mp_pose = mp.solutions.pose
    drawing_utils = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles

    output_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    saved_count = 0
    with mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        enable_segmentation=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    ) as pose:
        for original_frame in range(start_frame, end_frame, 5):
            processed_frame = original_frame - start_frame
            filename = f"processed_{processed_frame:06d}_frame_{original_frame:06d}.jpg"
            output_path = output_dir / filename
            if save_review_frame(
                cap,
                pose,
                mp_pose,
                drawing_utils,
                drawing_styles,
                fps,
                start_frame,
                report,
                original_frame,
                output_path,
            ):
                saved_count += 1

    cap.release()
    print(f"Saved all review frames: {output_dir} ({saved_count} images)")


def output_path(output_dir, output_prefix, filename):
    """Build an output path, adding the optional prefix before the filename."""
    if output_prefix:
        filename = f"{output_prefix}_{filename}"
    return output_dir / filename


def main():
    """Run the full MVP pipeline."""
    args = parse_args()
    video_path = Path(args.video_path)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    landmarks_csv_path = output_path(output_dir, args.output_prefix, "landmarks.csv")
    report_json_path = output_path(output_dir, args.output_prefix, "timing_report.json")
    plot_path = output_path(output_dir, args.output_prefix, "angles_plot.png")
    overlay_path = output_path(output_dir, args.output_prefix, "pose_overlay.mp4")
    event_review_dir = review_dir_path(output_dir, args.output_prefix, "review_frames")
    all_review_dir = review_dir_path(output_dir, args.output_prefix, "all_review_frames")

    fps, original_total_frames, width, height = get_video_info(video_path)
    start_frame, end_frame, processed_start_time, processed_end_time = resolve_processing_range(
        fps,
        original_total_frames,
        args.start_time,
        args.end_time,
    )

    df, landmark_detection_rate = extract_landmarks(video_path, fps, start_frame, end_frame)
    df = add_calculations(df, fps, args.smoothing_window, args.throwing_hand)

    report = build_timing_report(
        df=df,
        fps=fps,
        original_total_frames=original_total_frames,
        processed_start_time=processed_start_time,
        processed_end_time=processed_end_time,
        landmark_detection_rate=landmark_detection_rate,
        throwing_hand=args.throwing_hand,
        manual_front_foot_strike_frame=args.front_foot_strike_frame,
        manual_pelvis_peak_frame=args.pelvis_peak_frame,
        manual_trunk_peak_frame=args.trunk_peak_frame,
        manual_ball_release_frame=args.ball_release_frame,
        peak_search_start_ms=args.peak_search_start_ms,
        pelvis_peak_search_end_ms=args.pelvis_peak_search_end_ms,
        trunk_peak_search_end_ms=args.trunk_peak_search_end_ms,
        ball_release_search_start_ms=args.ball_release_search_start_ms,
        ball_release_search_end_ms=args.ball_release_search_end_ms,
    )

    df.to_csv(landmarks_csv_path, index=False)
    write_timing_report(report, report_json_path)
    write_angles_plot(df, report, plot_path)
    write_pose_overlay_video(
        video_path,
        fps,
        width,
        height,
        start_frame,
        end_frame,
        report,
        df,
        overlay_path,
    )

    if args.export_event_review:
        export_event_review_frames(
            video_path,
            fps,
            start_frame,
            end_frame,
            report,
            event_review_dir,
        )

    if args.export_all_review_frames:
        export_all_review_frames(
            video_path,
            fps,
            start_frame,
            end_frame,
            report,
            all_review_dir,
        )

    print(f"Saved landmarks: {landmarks_csv_path}")
    print(f"Saved timing report: {report_json_path}")
    print(f"Saved angle plot: {plot_path}")
    print(f"Saved pose overlay video: {overlay_path}")
    print(report["sequence_result"])


if __name__ == "__main__":
    main()
