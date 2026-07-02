#!/usr/bin/env python3
"""Stress-test local event detection against landmark jitter and dropout.

The harness never changes a source video, landmark CSV, timing report, or the
detector. It copies one landmark sequence in memory, injects controlled noise,
reuses the analyzer's existing event functions, and measures frame shifts.
"""

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

import analyze_pitch_timing as analyzer


EVENT_COLUMNS = {
    "front_foot_strike": "front_foot_strike_frame",
    "pelvis_peak": "pelvis_peak_frame",
    "trunk_peak": "trunk_peak_frame",
    "ball_release": "ball_release_frame",
}


def parse_args():
    """Parse local robustness harness options."""
    parser = argparse.ArgumentParser(
        description="Stress-test existing pitch timing outputs without changing them."
    )
    parser.add_argument("--landmarks", required=True, help="Path to landmarks CSV.")
    parser.add_argument("--timing-report", required=True, help="Path to timing report JSON.")
    parser.add_argument("--throwing-hand", choices=["right", "left"], required=True)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument("--jitter-levels", default="0,0.002,0.005")
    parser.add_argument("--dropout-rates", default="0,0.05,0.10")
    parser.add_argument("--smoothing-window", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--output-prefix", default="robustness_stress")
    return parser.parse_args()


def parse_float_list(text, argument_name):
    """Parse a comma-separated list of non-negative floats."""
    try:
        values = [float(value.strip()) for value in text.split(",") if value.strip()]
    except ValueError as error:
        raise ValueError(f"Invalid {argument_name}: {text}") from error
    if not values or any(value < 0 for value in values):
        raise ValueError(f"{argument_name} must contain non-negative values.")
    return values


def load_json(path):
    """Load a JSON report."""
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def add_noise_and_dropout(dataframe, jitter, dropout_rate, random_generator):
    """Return a copy with normalized-coordinate jitter and landmark dropouts."""
    result = dataframe.copy()
    landmark_prefixes = [
        column[: -len("_x")]
        for column in result.columns
        if column.endswith("_x") and f"{column[: -len('_x')]}_y" in result.columns
    ]
    for prefix in landmark_prefixes:
        x_column = f"{prefix}_x"
        y_column = f"{prefix}_y"
        visibility_column = f"{prefix}_visibility"
        valid = result[x_column].notna() & result[y_column].notna()
        valid_indices = np.flatnonzero(valid.to_numpy())
        if jitter and len(valid_indices):
            noise = random_generator.normal(0.0, jitter, size=(len(valid_indices), 2))
            result.loc[valid, x_column] = np.clip(
                result.loc[valid, x_column].to_numpy() + noise[:, 0], 0.0, 1.0
            )
            result.loc[valid, y_column] = np.clip(
                result.loc[valid, y_column].to_numpy() + noise[:, 1], 0.0, 1.0
            )
        if dropout_rate and len(valid_indices):
            dropped_indices = valid_indices[
                random_generator.random(len(valid_indices)) < dropout_rate
            ]
            if len(dropped_indices):
                result.loc[dropped_indices, [x_column, y_column]] = np.nan
                if visibility_column in result.columns:
                    result.loc[dropped_indices, visibility_column] = np.nan
    return result


def event_frames_from_dataframe(dataframe, report, throwing_hand, fps):
    """Run the existing auto event functions on an in-memory landmark sequence."""
    front_foot = analyzer.detect_front_foot_strike(dataframe, throwing_hand, fps)
    ffs_frame = front_foot.get("frame")
    if ffs_frame is None:
        return {event: None for event in EVENT_COLUMNS}

    peak_start_ms = float(report.get("peak_search_start_ms", 0.0))
    pelvis_end_ms = float(report.get("pelvis_peak_search_end_ms", 300.0))
    trunk_end_ms = float(report.get("trunk_peak_search_end_ms", 350.0))
    release_start_ms = float(report.get("ball_release_search_start_ms", 30.0))
    release_end_ms = float(report.get("ball_release_search_end_ms", 250.0))
    pelvis_start, pelvis_end = analyzer.peak_search_window_frames(
        ffs_frame, fps, peak_start_ms, pelvis_end_ms
    )
    trunk_start, trunk_end = analyzer.peak_search_window_frames(
        ffs_frame, fps, peak_start_ms, trunk_end_ms
    )
    pelvis = analyzer.detect_pelvis_peak(dataframe, pelvis_start, pelvis_end).get("frame")
    trunk = analyzer.peak_in_frame_window(
        dataframe, "shoulder_angular_velocity", trunk_start, trunk_end
    )
    release = None
    if trunk is not None:
        release = analyzer.detect_ball_release(
            dataframe,
            throwing_hand,
            trunk,
            fps,
            release_start_ms,
            release_end_ms,
        ).get("frame")
    return {
        "front_foot_strike": ffs_frame,
        "pelvis_peak": pelvis,
        "trunk_peak": trunk,
        "ball_release": release,
    }


def summarize_condition(rows, event_name):
    """Return robust statistics for one event under one stress condition."""
    shifts = [
        abs(row[f"{event_name}_frame_shift"])
        for row in rows
        if row.get(f"{event_name}_frame_shift") is not None
    ]
    detected_fraction = sum(
        row.get(f"{event_name}_detected_frame") is not None for row in rows
    ) / len(rows) if rows else 0.0
    if not shifts:
        return {
            "event": event_name,
            "detected_fraction": detected_fraction,
            "mean_absolute_frame_shift": None,
            "median_absolute_frame_shift": None,
            "p90_absolute_frame_shift": None,
        }
    return {
        "event": event_name,
        "detected_fraction": detected_fraction,
        "mean_absolute_frame_shift": float(np.mean(shifts)),
        "median_absolute_frame_shift": float(np.median(shifts)),
        "p90_absolute_frame_shift": float(np.percentile(shifts, 90)),
    }


def write_csv(path, rows):
    """Write trial data to CSV."""
    fields = list(rows[0]) if rows else ["trial", "jitter", "dropout_rate"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    """Run local robustness simulations and save CSV/JSON artifacts."""
    args = parse_args()
    if args.trials < 1:
        raise ValueError("--trials must be at least 1.")
    jitters = parse_float_list(args.jitter_levels, "--jitter-levels")
    dropouts = parse_float_list(args.dropout_rates, "--dropout-rates")
    report = load_json(args.timing_report)
    source = pd.read_csv(args.landmarks)
    fps = float(report.get("fps", 0.0))
    if fps <= 0:
        raise ValueError("Timing report must contain a positive fps value.")

    baseline_dataframe = analyzer.add_calculations(
        source, fps, args.smoothing_window, args.throwing_hand
    )
    baseline_events = event_frames_from_dataframe(
        baseline_dataframe, report, args.throwing_hand, fps
    )
    generator = np.random.default_rng(args.seed)
    rows = []
    for jitter in jitters:
        for dropout_rate in dropouts:
            for trial in range(args.trials):
                perturbed = add_noise_and_dropout(
                    source, jitter, dropout_rate, generator
                )
                calculated = analyzer.add_calculations(
                    perturbed, fps, args.smoothing_window, args.throwing_hand
                )
                detected = event_frames_from_dataframe(
                    calculated, report, args.throwing_hand, fps
                )
                row = {
                    "trial": trial + 1,
                    "jitter": jitter,
                    "dropout_rate": dropout_rate,
                }
                for event_name, report_column in EVENT_COLUMNS.items():
                    baseline_frame = baseline_events.get(event_name)
                    detected_frame = detected.get(event_name)
                    row[f"{event_name}_baseline_frame"] = baseline_frame
                    row[f"{event_name}_report_frame"] = report.get(report_column)
                    row[f"{event_name}_detected_frame"] = detected_frame
                    row[f"{event_name}_frame_shift"] = (
                        int(detected_frame) - int(baseline_frame)
                        if detected_frame is not None and baseline_frame is not None
                        else None
                    )
                rows.append(row)

    summaries = []
    for jitter in jitters:
        for dropout_rate in dropouts:
            condition_rows = [
                row for row in rows
                if row["jitter"] == jitter and row["dropout_rate"] == dropout_rate
            ]
            for event_name in EVENT_COLUMNS:
                summary = summarize_condition(condition_rows, event_name)
                summary.update({"jitter": jitter, "dropout_rate": dropout_rate})
                summaries.append(summary)

    zero_noise_rows = [
        row for row in rows if row["jitter"] == 0.0 and row["dropout_rate"] == 0.0
    ]
    zero_noise_discrepancies = []
    for row in zero_noise_rows:
        for event_name in EVENT_COLUMNS:
            if row.get(f"{event_name}_frame_shift") not in {0, None}:
                zero_noise_discrepancies.append(
                    {
                        "trial": row["trial"],
                        "event": event_name,
                        "frame_shift": row[f"{event_name}_frame_shift"],
                    }
                )

    outputs_dir = Path(args.output_dir)
    outputs_dir.mkdir(parents=True, exist_ok=True)
    trials_csv = outputs_dir / f"{args.output_prefix}_trials.csv"
    summary_json = outputs_dir / f"{args.output_prefix}_summary.json"
    write_csv(trials_csv, rows)
    payload = {
        "source_landmarks": str(args.landmarks),
        "source_timing_report": str(args.timing_report),
        "throwing_hand": args.throwing_hand,
        "fps": fps,
        "seed": args.seed,
        "smoothing_window": args.smoothing_window,
        "trials_per_condition": args.trials,
        "jitter_levels": jitters,
        "dropout_rates": dropouts,
        "baseline_auto_events": baseline_events,
        "timing_report_events": {
            event_name: report.get(column) for event_name, column in EVENT_COLUMNS.items()
        },
        "condition_summaries": summaries,
        "zero_noise_baseline_ok": not zero_noise_discrepancies,
        "zero_noise_discrepancies": zero_noise_discrepancies,
        "trials_csv": str(trials_csv),
    }
    with summary_json.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)

    print(f"Baseline auto events: {baseline_events}")
    print(f"Zero-noise baseline check: {'PASS' if not zero_noise_discrepancies else 'WARNING'}")
    print(f"Stress trials written: {len(rows)}")
    print(f"Saved trials CSV: {trials_csv}")
    print(f"Saved stress summary: {summary_json}")


if __name__ == "__main__":
    main()
