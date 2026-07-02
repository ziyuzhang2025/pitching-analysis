#!/usr/bin/env python3
"""Create local pose-quality, event-confidence, and review-queue reports.

This harness reads existing ``*_timing_report.json`` and ``*_landmarks.csv``
files. It does not rerun MediaPipe, alter event detection, or use a cloud API.
Its purpose is to identify pitches and event frames that deserve visual review.
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


NO_ARM_WARNING = "No major 2D throwing arm quality warning."
NO_SEPARATION_WARNING = "No major 2D separation quality warning."


def parse_args():
    """Parse local reliability harness options."""
    parser = argparse.ArgumentParser(
        description="Score pose and event reliability from existing local outputs."
    )
    parser.add_argument("--outputs-dir", default="outputs")
    parser.add_argument(
        "--filename-contains",
        default=None,
        help="Only inspect timing report filenames containing this text.",
    )
    parser.add_argument("--output-prefix", default="pose_reliability")
    parser.add_argument("--review-limit", type=int, default=20)
    parser.add_argument("--low-confidence-threshold", type=float, default=0.5)
    parser.add_argument("--visibility-threshold", type=float, default=0.6)
    parser.add_argument(
        "--visibility-percentile",
        type=float,
        default=10.0,
        help="Low-percentile visibility to report for each pitch (default: 10).",
    )
    parser.add_argument("--min-detection-rate", type=float, default=0.85)
    parser.add_argument("--recommended-min-fps", type=float, default=60.0)
    return parser.parse_args()


def load_json(path):
    """Load a JSON file using UTF-8."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def safe_float(value):
    """Return a finite float or None."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if np.isfinite(result) else None


def report_prefix(report_path):
    """Return the output prefix represented by one timing report path."""
    suffix = "_timing_report.json"
    if not report_path.name.endswith(suffix):
        raise ValueError(f"Unexpected timing report name: {report_path.name}")
    return report_path.name[: -len(suffix)]


def visibility_summary(landmarks_path, threshold, percentile):
    """Summarize landmark visibility without assuming every CSV version matches."""
    if not landmarks_path.exists():
        return {
            "landmarks_found": False,
            "mean_visibility": None,
            "low_percentile_visibility": None,
            "low_visibility_fraction": None,
            "pose_detected_fraction": None,
        }

    dataframe = pd.read_csv(landmarks_path)
    visibility_columns = [
        column for column in dataframe.columns if column.endswith("_visibility")
    ]
    values = dataframe[visibility_columns].to_numpy().astype(float).ravel()
    values = values[np.isfinite(values)]
    pose_detected = dataframe.get("pose_detected")
    pose_fraction = None
    if pose_detected is not None and len(pose_detected):
        pose_fraction = float(pd.Series(pose_detected).fillna(False).astype(bool).mean())

    if not len(values):
        return {
            "landmarks_found": True,
            "mean_visibility": None,
            "low_percentile_visibility": None,
            "low_visibility_fraction": None,
            "pose_detected_fraction": pose_fraction,
        }
    return {
        "landmarks_found": True,
        "mean_visibility": float(np.mean(values)),
        "low_percentile_visibility": float(np.percentile(values, percentile)),
        "low_visibility_fraction": float(np.mean(values < threshold)),
        "pose_detected_fraction": pose_fraction,
    }


def event_at_window_edge(report, event_name):
    """Return True when an event lies at or one frame from its search edge."""
    frame = report.get(f"{event_name}_frame")
    start = report.get(f"{event_name}_search_start_frame")
    end = report.get(f"{event_name}_search_end_frame")
    if frame is None or start is None or end is None:
        return False
    try:
        return int(frame) <= int(start) + 1 or int(frame) >= int(end) - 1
    except (TypeError, ValueError):
        return False


def reliability_row(
    report_path,
    report,
    visibility,
    args,
):
    """Create one score row and a concrete visual-review recommendation."""
    reasons = []
    risk_score = 0
    fps = safe_float(report.get("fps"))
    detection_rate = safe_float(report.get("landmark_detection_rate"))
    ffs_confidence = safe_float(report.get("front_foot_strike_confidence"))
    release_confidence = safe_float(report.get("ball_release_confidence"))
    mean_visibility = visibility["mean_visibility"]
    low_percentile_visibility = visibility["low_percentile_visibility"]
    low_visibility_fraction = visibility["low_visibility_fraction"]

    if fps is not None and fps < args.recommended_min_fps:
        reasons.append("low_fps")
        risk_score += 1
    if detection_rate is not None and detection_rate < args.min_detection_rate:
        reasons.append("low_pose_detection_rate")
        risk_score += 3
    if mean_visibility is not None and mean_visibility < args.visibility_threshold:
        reasons.append("low_landmark_visibility")
        risk_score += 3
    if (
        low_percentile_visibility is not None
        and low_percentile_visibility < args.visibility_threshold
    ):
        reasons.append("low_percentile_visibility")
        risk_score += 1
    if low_visibility_fraction is not None and low_visibility_fraction > 0.25:
        reasons.append("frequent_low_visibility")
        risk_score += 2
    if not visibility["landmarks_found"]:
        reasons.append("missing_landmarks_csv")
        risk_score += 3
    if ffs_confidence is not None and ffs_confidence < args.low_confidence_threshold:
        reasons.append("low_ffs_confidence")
        risk_score += 3
    if release_confidence is not None and release_confidence < args.low_confidence_threshold:
        reasons.append("low_release_confidence")
        risk_score += 2
    if event_at_window_edge(report, "pelvis_peak"):
        reasons.append("pelvis_peak_at_search_edge")
        risk_score += 2
    if event_at_window_edge(report, "trunk_peak"):
        reasons.append("trunk_peak_at_search_edge")
        risk_score += 2
    if event_at_window_edge(report, "ball_release"):
        reasons.append("release_at_search_edge")
        risk_score += 2

    sequence = report.get("sequence_classification")
    if sequence in {"trunk_before_pelvis", "peak_before_front_foot_strike", "unclear"}:
        reasons.append("sequence_needs_review")
        risk_score += 2
    if sequence == "pelvis_trunk_near_simultaneous":
        reasons.append("pelvis_trunk_near_simultaneous")
        risk_score += 1

    arm_warning = report.get("throwing_arm_quality_warning")
    if arm_warning and arm_warning != NO_ARM_WARNING:
        reasons.append("throwing_arm_quality_warning")
        risk_score += 1
    separation_warning = report.get("hip_shoulder_separation_quality_warning")
    if separation_warning and separation_warning != NO_SEPARATION_WARNING:
        reasons.append("separation_quality_warning")
        risk_score += 1

    if "low_ffs_confidence" in reasons:
        primary_event = "front_foot_strike"
    elif "low_release_confidence" in reasons or "release_at_search_edge" in reasons:
        primary_event = "ball_release"
    elif "pelvis_peak_at_search_edge" in reasons:
        primary_event = "pelvis_peak"
    elif "trunk_peak_at_search_edge" in reasons:
        primary_event = "trunk_peak"
    else:
        primary_event = "front_foot_strike"

    event_frame = report.get(f"{primary_event}_frame")
    review_start = int(event_frame) - 10 if event_frame is not None else None
    review_end = int(event_frame) + 10 if event_frame is not None else None
    prefix = report_prefix(report_path)
    return {
        "report_prefix": prefix,
        "timing_report_path": str(report_path),
        "landmarks_path": str(report_path.with_name(f"{prefix}_landmarks.csv")),
        "fps": fps,
        "processed_frame_count": report.get("processed_frame_count"),
        "landmark_detection_rate": detection_rate,
        "pose_detected_fraction": visibility["pose_detected_fraction"],
        "mean_landmark_visibility": mean_visibility,
        "low_percentile_landmark_visibility": low_percentile_visibility,
        "low_visibility_fraction": low_visibility_fraction,
        "front_foot_strike_frame": report.get("front_foot_strike_frame"),
        "front_foot_strike_confidence": ffs_confidence,
        "pelvis_peak_frame": report.get("pelvis_peak_frame"),
        "trunk_peak_frame": report.get("trunk_peak_frame"),
        "ball_release_frame": report.get("ball_release_frame"),
        "ball_release_confidence": release_confidence,
        "sequence_classification": sequence,
        "risk_score": risk_score,
        "review_priority": "high" if risk_score >= 6 else "medium" if risk_score >= 3 else "low",
        "primary_review_event": primary_event,
        "suggested_review_start_frame": review_start,
        "suggested_review_end_frame": review_end,
        "risk_reasons": ";".join(reasons) if reasons else "no_major_reliability_risk",
    }


def write_csv(path, rows):
    """Write CSV even when no reports were found."""
    fields = list(rows[0]) if rows else ["report_prefix", "risk_score", "risk_reasons"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Run the local reliability harness."""
    args = parse_args()
    outputs_dir = Path(args.outputs_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    report_paths = sorted(outputs_dir.glob("*_timing_report.json"))
    if args.filename_contains:
        report_paths = [path for path in report_paths if args.filename_contains in path.name]

    rows = []
    for path in report_paths:
        report = load_json(path)
        prefix = report_prefix(path)
        landmarks_path = outputs_dir / f"{prefix}_landmarks.csv"
        visibility = visibility_summary(
            landmarks_path,
            args.visibility_threshold,
            args.visibility_percentile,
        )
        rows.append(reliability_row(path, report, visibility, args))

    rows.sort(key=lambda row: (-row["risk_score"], row["report_prefix"]))
    review_rows = rows[: max(0, args.review_limit)]
    reliability_csv = outputs_dir / f"{args.output_prefix}_pose_reliability.csv"
    review_csv = outputs_dir / f"{args.output_prefix}_review_queue.csv"
    summary_json = outputs_dir / f"{args.output_prefix}_pose_reliability_summary.json"
    write_csv(reliability_csv, rows)
    write_csv(review_csv, review_rows)

    reason_counts = Counter()
    for row in rows:
        reason_counts.update(row["risk_reasons"].split(";"))
    summary = {
        "reports_scanned": len(rows),
        "high_priority_review_count": sum(row["review_priority"] == "high" for row in rows),
        "medium_priority_review_count": sum(row["review_priority"] == "medium" for row in rows),
        "low_priority_review_count": sum(row["review_priority"] == "low" for row in rows),
        "risk_reason_counts": dict(sorted(reason_counts.items())),
        "thresholds": {
            "low_confidence_threshold": args.low_confidence_threshold,
            "visibility_threshold": args.visibility_threshold,
            "visibility_percentile": args.visibility_percentile,
            "min_detection_rate": args.min_detection_rate,
            "recommended_min_fps": args.recommended_min_fps,
        },
        "reliability_csv": str(reliability_csv),
        "review_queue_csv": str(review_csv),
    }
    with summary_json.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=2)

    print(f"Reports scanned: {len(rows)}")
    print(f"High-priority reviews: {summary['high_priority_review_count']}")
    print(f"Saved reliability CSV: {reliability_csv}")
    print(f"Saved review queue CSV: {review_csv}")
    print(f"Saved reliability summary: {summary_json}")


if __name__ == "__main__":
    main()
