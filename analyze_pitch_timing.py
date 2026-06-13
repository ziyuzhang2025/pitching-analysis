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
    "left_wrist",
    "right_wrist",
]

EVENT_SPECS = [
    ("front_foot_strike_frame", "FRONT FOOT STRIKE", (0, 255, 0), "front_foot_strike"),
    ("pelvis_peak_frame", "PELVIS PEAK", (0, 165, 255), "pelvis_peak"),
    ("trunk_peak_frame", "TRUNK PEAK", (0, 0, 255), "trunk_peak"),
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


def detect_front_foot_strike(df, throwing_hand):
    """
    Approximate front foot strike from the lead ankle's y position.

    For a right-handed pitcher, the lead foot is usually the left foot.
    For a left-handed pitcher, the lead foot is usually the right foot.

    MediaPipe y coordinates are normalized image coordinates where larger y
    means lower in the image. This function looks for a local maximum in lead
    ankle y, followed by at least 5 frames where the ankle stays roughly stable.
    """
    lead_ankle = "left_ankle" if throwing_hand == "right" else "right_ankle"
    y = df[f"{lead_ankle}_y"].astype(float).interpolate(limit_direction="both")

    if y.isna().all():
        return None

    stable_frames_required = 5
    # Normalized image coordinates usually range 0-1. This tolerance is a
    # simple MVP threshold for "not moving much vertically."
    stability_tolerance = 0.015

    values = y.to_numpy()
    total = len(values)

    for row_position in range(1, total - stable_frames_required):
        previous_y = values[row_position - 1]
        current_y = values[row_position]
        next_values = values[row_position + 1 : row_position + 1 + stable_frames_required]

        is_local_maximum = current_y >= previous_y and current_y >= np.nanmax(next_values)
        becomes_stable = np.nanmax(next_values) - np.nanmin(next_values) <= stability_tolerance

        if is_local_maximum and becomes_stable:
            return int(df.iloc[row_position]["frame"])

    # Fallback: if the local-maximum-and-stability rule fails, use the lowest
    # visible lead ankle position inside the processed segment.
    fallback_position = int(np.nanargmax(values))
    return int(df.iloc[fallback_position]["frame"])


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


def add_calculations(df, fps, smoothing_window):
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

    df["shoulder_angular_velocity"] = angular_velocity_degrees_per_second(
        df["shoulder_angle_smoothed"], fps
    )
    df["hip_angular_velocity"] = angular_velocity_degrees_per_second(
        df["hip_angle_smoothed"], fps
    )

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
    peak_search_start_ms,
    pelvis_peak_search_end_ms,
    trunk_peak_search_end_ms,
):
    """Detect or accept event frames and build the JSON-ready timing report."""
    auto_front_foot_strike_frame = detect_front_foot_strike(df, throwing_hand)
    front_foot_strike_frame, front_foot_method = choose_event(
        manual_front_foot_strike_frame, auto_front_foot_strike_frame
    )

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

    return {
        "fps": fps,
        "original_total_frames": int(original_total_frames),
        "processed_start_time": processed_start_time,
        "processed_end_time": processed_end_time,
        "processed_frame_count": int(len(df)),
        "peak_search_start_ms": peak_search_start_ms,
        "pelvis_peak_search_end_ms": pelvis_peak_search_end_ms,
        "trunk_peak_search_end_ms": trunk_peak_search_end_ms,
        "pelvis_peak_search_start_frame": pelvis_search_start_frame,
        "pelvis_peak_search_end_frame": pelvis_search_end_frame,
        "trunk_peak_search_start_frame": trunk_search_start_frame,
        "trunk_peak_search_end_frame": trunk_search_end_frame,
        "front_foot_strike_frame": front_foot_strike_frame,
        "pelvis_peak_frame": pelvis_peak_frame,
        "trunk_peak_frame": trunk_peak_frame,
        "front_foot_strike_detection_method": front_foot_method,
        "pelvis_peak_detection_method": pelvis_method,
        "trunk_peak_detection_method": trunk_method,
        "front_foot_strike_time": frame_to_time(front_foot_strike_frame, fps),
        "pelvis_peak_time": frame_to_time(pelvis_peak_frame, fps),
        "trunk_peak_time": frame_to_time(trunk_peak_frame, fps),
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


def draw_exact_event_label(frame_bgr, original_frame, report):
    """Draw an event label only on the exact selected event frame."""
    y = 125
    for report_key, label, color, _slug in EVENT_SPECS:
        event_frame = report.get(report_key)
        if event_frame is not None and original_frame == event_frame:
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
    y = 95
    for report_key, label, color, _slug in EVENT_SPECS:
        event_frame = report.get(report_key)
        if event_frame is not None and event_frame <= original_frame < event_frame + 5:
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


def write_pose_overlay_video(video_path, fps, width, height, start_frame, end_frame, report, output_path):
    """Create an MP4 with MediaPipe skeleton, frame/time text, and event labels."""
    mp_pose = mp.solutions.pose
    drawing_utils = mp.solutions.drawing_utils
    drawing_styles = mp.solutions.drawing_styles

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
    df = add_calculations(df, fps, args.smoothing_window)

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
        peak_search_start_ms=args.peak_search_start_ms,
        pelvis_peak_search_end_ms=args.pelvis_peak_search_end_ms,
        trunk_peak_search_end_ms=args.trunk_peak_search_end_ms,
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
