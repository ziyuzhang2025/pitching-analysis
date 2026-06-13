#!/usr/bin/env python3
"""
Summarize multiple local pitching timing reports.

This script reads *_timing_report.json files from the outputs folder, optionally
filters them, calculates simple timing intervals, writes a CSV summary, and
prints a short terminal summary.

No cloud API is used. No API key is required.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


OUTPUTS_DIR = Path("outputs")
SUMMARY_CSV_PATH = OUTPUTS_DIR / "pitch_summary.csv"
FILTERED_SUMMARY_CSV_PATH = OUTPUTS_DIR / "pitch_summary_filtered.csv"
CORRECT_SEQUENCE_MESSAGE = (
    "Basic sequence looks correct: front foot strike -> pelvis -> trunk."
)


REPORT_FIELDS = [
    "fps",
    "front_foot_strike_frame",
    "pelvis_peak_frame",
    "trunk_peak_frame",
    "front_foot_strike_time",
    "pelvis_peak_time",
    "trunk_peak_time",
    "front_foot_strike_detection_method",
    "pelvis_peak_detection_method",
    "trunk_peak_detection_method",
    "sequence_result",
    "landmark_detection_rate",
]

SUMMARY_COLUMNS = [
    "filename",
    *REPORT_FIELDS,
    "ffs_to_pelvis_ms",
    "pelvis_to_trunk_ms",
    "ffs_to_trunk_ms",
]


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Summarize local pitching timing JSON reports."
    )
    parser.add_argument(
        "--filename-contains",
        default=None,
        help="Only include report files whose filename contains this text.",
    )
    parser.add_argument(
        "--require-manual-front-foot-strike",
        action="store_true",
        help='Only include reports where front_foot_strike_detection_method is "manual".',
    )
    parser.add_argument(
        "--require-correct-sequence",
        action="store_true",
        help="Only include reports with the basic correct sequence result.",
    )
    return parser.parse_args()


def seconds_to_ms_delta(later_time, earlier_time):
    """Return the difference between two second timestamps in milliseconds."""
    if later_time is None or earlier_time is None:
        return None
    return (later_time - earlier_time) * 1000.0


def load_report(report_path):
    """Load one timing report and convert it to a summary row."""
    with report_path.open("r", encoding="utf-8") as f:
        report = json.load(f)

    row = {"filename": report_path.name}
    for field in REPORT_FIELDS:
        row[field] = report.get(field)

    ffs_time = report.get("front_foot_strike_time")
    pelvis_time = report.get("pelvis_peak_time")
    trunk_time = report.get("trunk_peak_time")

    row["ffs_to_pelvis_ms"] = seconds_to_ms_delta(pelvis_time, ffs_time)
    row["pelvis_to_trunk_ms"] = seconds_to_ms_delta(trunk_time, pelvis_time)
    row["ffs_to_trunk_ms"] = seconds_to_ms_delta(trunk_time, ffs_time)

    return row


def filters_are_active(args):
    """Return True when any optional filter was provided."""
    return (
        args.filename_contains is not None
        or args.require_manual_front_foot_strike
        or args.require_correct_sequence
    )


def apply_filters(df, args):
    """Apply the optional summary filters."""
    filtered = df.copy()

    if args.filename_contains is not None:
        filtered = filtered[
            filtered["filename"].str.contains(
                args.filename_contains,
                regex=False,
                na=False,
            )
        ]

    if args.require_manual_front_foot_strike:
        filtered = filtered[
            filtered["front_foot_strike_detection_method"] == "manual"
        ]

    if args.require_correct_sequence:
        filtered = filtered[
            filtered["sequence_result"] == CORRECT_SEQUENCE_MESSAGE
        ]

    return filtered


def format_median(value):
    """Format a median value for terminal output."""
    if pd.isna(value):
        return "n/a"
    return f"{value:.1f} ms"


def main():
    """Read all timing reports, write a CSV summary, and print key stats."""
    args = parse_args()
    report_paths = sorted(OUTPUTS_DIR.glob("*_timing_report.json"))
    reports_found = len(report_paths)

    if not report_paths:
        output_path = (
            FILTERED_SUMMARY_CSV_PATH
            if filters_are_active(args)
            else SUMMARY_CSV_PATH
        )
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=SUMMARY_COLUMNS).to_csv(output_path, index=False)

        print("Reports found before filtering: 0")
        print("Reports included after filtering: 0")
        print("Reports excluded: 0")
        print("Correct sequence count: 0")
        print("Median FFS to pelvis: n/a")
        print("Median pelvis to trunk: n/a")
        print("Median FFS to trunk: n/a")
        print(f"Saved summary CSV: {output_path}")
        return

    rows = [load_report(report_path) for report_path in report_paths]
    df = pd.DataFrame(rows, columns=SUMMARY_COLUMNS)
    filtered_df = apply_filters(df, args)
    output_path = FILTERED_SUMMARY_CSV_PATH if filters_are_active(args) else SUMMARY_CSV_PATH

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    filtered_df.to_csv(output_path, index=False)

    correct_sequence_count = int(
        (filtered_df["sequence_result"] == CORRECT_SEQUENCE_MESSAGE).sum()
    )
    median_ffs_to_pelvis_ms = filtered_df["ffs_to_pelvis_ms"].median()
    median_pelvis_to_trunk_ms = filtered_df["pelvis_to_trunk_ms"].median()
    median_ffs_to_trunk_ms = filtered_df["ffs_to_trunk_ms"].median()

    print(f"Reports found before filtering: {reports_found}")
    print(f"Reports included after filtering: {len(filtered_df)}")
    print(f"Reports excluded: {reports_found - len(filtered_df)}")
    print(f"Correct sequence count: {correct_sequence_count}")
    print(f"Median FFS to pelvis: {format_median(median_ffs_to_pelvis_ms)}")
    print(f"Median pelvis to trunk: {format_median(median_pelvis_to_trunk_ms)}")
    print(f"Median FFS to trunk: {format_median(median_ffs_to_trunk_ms)}")
    print(f"Saved summary CSV: {output_path}")


if __name__ == "__main__":
    main()
