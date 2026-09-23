#!/usr/bin/env python3
"""
Evaluate automatic pitch event detection against manually labeled frames.

The script reads a labels JSON file, runs analyze_pitch_timing.py on each
labeled video window without manual event overrides, and compares automatic
event frames to the labels.

No cloud API is used. No API key is required.
"""

import argparse
import csv
import json
import statistics
import subprocess
import sys
from pathlib import Path

from pitch_labels import load_label_file, safe_token


OUTPUTS_DIR = Path("outputs")
EVALUATION_CSV_PATH = OUTPUTS_DIR / "pitch_accuracy_evaluation.csv"

EVENT_FIELDS = [
    "front_foot_strike_frame",
    "pelvis_peak_frame",
    "trunk_peak_frame",
    "ball_release_frame",
]


def frame_from_time(time_seconds, fps):
    """Convert a timestamp to an approximate full-video frame number."""
    if time_seconds is None or fps is None:
        return None
    try:
        return int(round(float(time_seconds) * float(fps)))
    except (TypeError, ValueError):
        return None


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate automatic pitch timing against labeled event frames."
    )
    parser.add_argument(
        "--labels",
        default="labels/pitch_labels.example.json",
        help="Path to labels JSON file.",
    )
    parser.add_argument(
        "--throwing-hand",
        choices=["right", "left"],
        default="right",
        help="Pitcher's throwing hand for automatic analysis.",
    )
    parser.add_argument(
        "--output-prefix",
        default="eval_accuracy",
        help="Prefix for per-pitch analyzer outputs.",
    )
    parser.add_argument(
        "--annotation",
        default=None,
        help="Schema v2 only: annotation key to evaluate against (default: each pitch's 'reference').",
    )
    parser.add_argument(
        "--split",
        choices=["dev", "test"],
        default=None,
        help="Schema v2 only: evaluate only pitches in this split.",
    )
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Optional CSV path (default: outputs/pitch_accuracy_evaluation.csv).",
    )
    return parser.parse_args()


def load_labels(labels_path, annotation_key=None, split=None):
    """Load labels (schema v1 or v2) as normalized pitch dictionaries."""
    return load_label_file(labels_path, annotation_key=annotation_key, split=split)


def pitch_output_prefix(base_prefix, pitch):
    """Build a unique output prefix per pitch (video stem + pitch id).

    Earlier versions used only pitch_id, so pitches named window_1 in two
    different videos overwrote each other's artifacts.
    """
    return f"{base_prefix}_{safe_token(pitch.get('pitch_uid'))}"


def run_analyzer_for_pitch(pitch, throwing_hand, output_prefix):
    """Run analyze_pitch_timing.py without manual event overrides."""
    command = [
        sys.executable,
        "analyze_pitch_timing.py",
        pitch["video_path"],
        "--throwing-hand",
        throwing_hand,
        "--start-time",
        str(pitch["start_time"]),
        "--end-time",
        str(pitch["end_time"]),
        "--output-prefix",
        output_prefix,
    ]

    print(f"Running automatic analysis for {pitch.get('pitch_id', output_prefix)}...")
    subprocess.run(command, check=True)


def load_timing_report(output_prefix):
    """Load a generated timing_report.json file."""
    report_path = OUTPUTS_DIR / f"{output_prefix}_timing_report.json"
    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def frame_error(auto_frame, labeled_frame):
    """Return signed and absolute frame error."""
    if auto_frame is None or labeled_frame is None:
        return None, None
    signed_error = int(auto_frame) - int(labeled_frame)
    return signed_error, abs(signed_error)


def event_frame_values(pitch):
    """Return labeled event frames in field order."""
    return [pitch.get(event_field) for event_field in EVENT_FIELDS]


def label_warning_messages(pitch, start_frame, end_frame):
    """Return warnings for labels that appear outside the expected frame window."""
    warnings = []
    labeled_frames = [
        frame for frame in event_frame_values(pitch) if frame is not None
    ]
    if start_frame is None or end_frame is None or not labeled_frames:
        return warnings

    outside_events = []
    for event_field in EVENT_FIELDS:
        frame = pitch.get(event_field)
        if frame is not None and not (start_frame <= int(frame) <= end_frame):
            outside_events.append(f"{event_field}={frame}")

    if outside_events:
        warnings.append(
            "WARNING: labeled event frame(s) outside the labeled window "
            f"[{start_frame}, {end_frame}]: {', '.join(outside_events)}"
        )

    window_length_frames = max(0, end_frame - start_frame)
    window_relative_like = (
        start_frame > window_length_frames
        and all(0 <= int(frame) <= window_length_frames for frame in labeled_frames)
    )
    if window_relative_like:
        warnings.append(
            "WARNING: labels look window-relative, not full-video absolute. "
            "Expected labels/pitch_labels.json to store absolute full-video frame "
            "numbers. Add start_frame to window-relative labels before evaluating."
        )

    return warnings


def print_pitch_debug(pitch, report):
    """Print per-pitch label and auto frame details before comparison."""
    fps = report.get("fps") or pitch.get("fps")
    start_frame = pitch.get("start_frame")
    end_frame = pitch.get("end_frame")
    if start_frame is None:
        start_frame = frame_from_time(pitch.get("start_time"), fps)
    if end_frame is None:
        end_frame = frame_from_time(pitch.get("end_time"), fps)

    print("\nPitch evaluation details:")
    print(f"  pitch_id: {pitch.get('pitch_id')}")
    print(f"  video_path: {pitch.get('video_path')}")
    print(f"  start_time/end_time: {pitch.get('start_time')} / {pitch.get('end_time')}")
    print(f"  start_frame/end_frame: {start_frame} / {end_frame}")

    for event_field in EVENT_FIELDS:
        event_name = event_field.replace("_frame", "")
        print(
            f"  labeled {event_name}: {pitch.get(event_field)} | "
            f"auto {event_name}: {report.get(event_field)}"
        )

    for warning in label_warning_messages(pitch, start_frame, end_frame):
        print(f"  {warning}")


def evaluate_pitch(pitch, throwing_hand, base_output_prefix):
    """Run one pitch and return a CSV-ready evaluation row."""
    output_prefix = pitch_output_prefix(base_output_prefix, pitch)
    pitch_hand = pitch.get("throwing_hand") or throwing_hand
    run_analyzer_for_pitch(pitch, pitch_hand, output_prefix)
    report = load_timing_report(output_prefix)
    fps = report.get("fps")
    start_frame = pitch.get("start_frame")
    end_frame = pitch.get("end_frame")
    if start_frame is None:
        start_frame = frame_from_time(pitch.get("start_time"), fps)
    if end_frame is None:
        end_frame = frame_from_time(pitch.get("end_time"), fps)
    print_pitch_debug(pitch, report)

    row = {
        "pitch_id": pitch.get("pitch_id"),
        "video_path": pitch.get("video_path"),
        "start_time": pitch.get("start_time"),
        "end_time": pitch.get("end_time"),
        "start_frame": start_frame,
        "end_frame": end_frame,
        "label_source": pitch.get("label_source"),
        "output_prefix": output_prefix,
        "fps": fps,
        "pitch_uid": pitch.get("pitch_uid"),
        "video_stem": Path(str(pitch.get("video_path", ""))).stem,
        "pitcher_id": pitch.get("pitcher_id"),
        "throwing_hand": pitch_hand,
        "view": pitch.get("view"),
        "split": pitch.get("split"),
        "annotation_key": pitch.get("annotation_key"),
        "detector_version": report.get("detector_version"),
    }

    for event_field in EVENT_FIELDS:
        labeled_frame = pitch.get(event_field)
        auto_frame = report.get(event_field)
        signed_error, absolute_error = frame_error(auto_frame, labeled_frame)
        event_name = event_field.replace("_frame", "")

        row[f"{event_name}_labeled_frame"] = labeled_frame
        row[f"{event_name}_auto_frame"] = auto_frame
        row[f"{event_name}_frame_error"] = signed_error
        row[f"{event_name}_absolute_frame_error"] = absolute_error

    return row


def csv_fields():
    """Return output CSV field order."""
    fields = [
        "pitch_id",
        "video_path",
        "start_time",
        "end_time",
        "start_frame",
        "end_frame",
        "label_source",
        "output_prefix",
        "fps",
    ]
    for event_field in EVENT_FIELDS:
        event_name = event_field.replace("_frame", "")
        fields.extend(
            [
                f"{event_name}_labeled_frame",
                f"{event_name}_auto_frame",
                f"{event_name}_frame_error",
                f"{event_name}_absolute_frame_error",
            ]
        )
    # New columns are appended so existing column positions stay unchanged.
    fields.extend(
        [
            "pitch_uid",
            "video_stem",
            "pitcher_id",
            "throwing_hand",
            "view",
            "split",
            "annotation_key",
            "detector_version",
        ]
    )
    return fields


def write_evaluation_csv(rows, csv_path=EVALUATION_CSV_PATH):
    """Save evaluation rows (default: outputs/pitch_accuracy_evaluation.csv)."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields())
        writer.writeheader()
        writer.writerows(rows)


def event_absolute_errors(rows, event_field):
    """Return available absolute frame errors for one event."""
    event_name = event_field.replace("_frame", "")
    column = f"{event_name}_absolute_frame_error"
    return [row[column] for row in rows if row.get(column) is not None]


def percentage_within(errors, threshold):
    """Return percentage of errors within a frame threshold."""
    if not errors:
        return None
    return (sum(error <= threshold for error in errors) / len(errors)) * 100.0


def print_event_summary(rows, event_field):
    """Print aggregate metrics for one event."""
    event_name = event_field.replace("_frame", "")
    errors = event_absolute_errors(rows, event_field)

    print(f"\n{event_name}:")
    if not errors:
        print("  mean absolute frame error: n/a")
        print("  median absolute frame error: n/a")
        print("  within 1 frame: n/a")
        print("  within 3 frames: n/a")
        print("  within 5 frames: n/a")
        return

    print(f"  mean absolute frame error: {statistics.mean(errors):.2f}")
    print(f"  median absolute frame error: {statistics.median(errors):.2f}")
    print(f"  within 1 frame: {percentage_within(errors, 1):.1f}%")
    print(f"  within 3 frames: {percentage_within(errors, 3):.1f}%")
    print(f"  within 5 frames: {percentage_within(errors, 5):.1f}%")


def print_summary(rows, csv_path=EVALUATION_CSV_PATH):
    """Print aggregate accuracy summary."""
    print(f"\nPitches evaluated: {len(rows)}")
    for event_field in EVENT_FIELDS:
        print_event_summary(rows, event_field)
    print(f"\nSaved evaluation CSV: {csv_path}")


def main():
    """CLI entry point."""
    args = parse_args()
    pitches = load_labels(args.labels, annotation_key=args.annotation, split=args.split)
    rows = [
        evaluate_pitch(pitch, args.throwing_hand, args.output_prefix)
        for pitch in pitches
    ]
    csv_path = Path(args.output_csv) if args.output_csv else EVALUATION_CSV_PATH
    write_evaluation_csv(rows, csv_path)
    print_summary(rows, csv_path)


if __name__ == "__main__":
    main()
