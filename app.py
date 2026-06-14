#!/usr/bin/env python3
"""
Local Streamlit UI for the baseball pitching timing analyzer.

The UI does not perform pose analysis itself. It builds a command and calls
analyze_pitch_timing.py with subprocess, then displays the generated outputs.
"""

import json
import shlex
import subprocess
import sys
from pathlib import Path

import streamlit as st


OUTPUTS_DIR = Path("outputs")


def output_path(output_prefix, filename):
    """Return the expected output path for a possibly-prefixed analyzer file."""
    if output_prefix:
        filename = f"{output_prefix}_{filename}"
    return OUTPUTS_DIR / filename


def optional_int(value):
    """Convert a text field to int, allowing blanks."""
    value = value.strip()
    if not value:
        return None
    return int(value)


def build_command(options):
    """Build the analyze_pitch_timing.py command from UI options."""
    command = [
        sys.executable,
        "analyze_pitch_timing.py",
        options["video_path"],
        "--throwing-hand",
        options["throwing_hand"],
        "--start-time",
        str(options["start_time"]),
        "--end-time",
        str(options["end_time"]),
        "--peak-search-start-ms",
        str(options["peak_search_start_ms"]),
        "--pelvis-peak-search-end-ms",
        str(options["pelvis_peak_search_end_ms"]),
        "--trunk-peak-search-end-ms",
        str(options["trunk_peak_search_end_ms"]),
        "--ball-release-search-start-ms",
        str(options["ball_release_search_start_ms"]),
        "--ball-release-search-end-ms",
        str(options["ball_release_search_end_ms"]),
    ]

    optional_frames = [
        ("front_foot_strike_frame", "--front-foot-strike-frame"),
        ("pelvis_peak_frame", "--pelvis-peak-frame"),
        ("trunk_peak_frame", "--trunk-peak-frame"),
        ("ball_release_frame", "--ball-release-frame"),
    ]
    for option_name, argument_name in optional_frames:
        if options[option_name] is not None:
            command.extend([argument_name, str(options[option_name])])

    if options["output_prefix"]:
        command.extend(["--output-prefix", options["output_prefix"]])

    if options["export_event_review"]:
        command.append("--export-event-review")

    return command


def load_report(report_path):
    """Load timing_report.json from disk."""
    with report_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def display_metrics(report):
    """Show the main timing metrics from a report."""
    st.subheader("Key Metrics")

    metric_columns = st.columns(3)
    metric_columns[0].metric(
        "Front foot strike",
        report.get("front_foot_strike_frame", "n/a"),
    )
    metric_columns[1].metric(
        "FFS confidence",
        report.get("front_foot_strike_confidence", "n/a"),
    )
    metric_columns[2].metric(
        "Pelvis peak",
        report.get("pelvis_peak_frame", "n/a"),
    )

    metric_columns = st.columns(3)
    metric_columns[0].metric("Trunk peak", report.get("trunk_peak_frame", "n/a"))
    metric_columns[1].metric("Ball release", report.get("ball_release_frame", "n/a"))
    metric_columns[2].metric(
        "Release confidence",
        report.get("ball_release_confidence", "n/a"),
    )

    metric_columns = st.columns(4)
    metric_columns[0].metric(
        "Pelvis window end",
        report.get("pelvis_peak_search_end_ms", "n/a"),
    )
    metric_columns[1].metric(
        "Trunk window end",
        report.get("trunk_peak_search_end_ms", "n/a"),
    )
    metric_columns[2].metric(
        "Release window start",
        report.get("ball_release_search_start_ms", "n/a"),
    )
    metric_columns[3].metric(
        "Release window end",
        report.get("ball_release_search_end_ms", "n/a"),
    )

    st.write("Sequence result:")
    st.info(report.get("sequence_result", "n/a"))


def display_outputs(output_prefix):
    """Display report JSON, angle plot, and pose overlay if they exist."""
    report_path = output_path(output_prefix, "timing_report.json")
    plot_path = output_path(output_prefix, "angles_plot.png")
    overlay_path = output_path(output_prefix, "pose_overlay.mp4")

    if not report_path.exists():
        st.error(f"Timing report not found: {report_path}")
        return

    report = load_report(report_path)
    display_metrics(report)

    st.subheader("Timing Report JSON")
    st.json(report)

    if plot_path.exists():
        st.subheader("Angles Plot")
        st.image(str(plot_path))
    else:
        st.warning(f"Angles plot not found: {plot_path}")

    if overlay_path.exists():
        st.subheader("Pose Overlay Video")
        st.video(str(overlay_path))
    else:
        st.warning(f"Pose overlay video not found: {overlay_path}")


def main():
    """Render the Streamlit app."""
    st.set_page_config(page_title="Baseball Pitching Timing Analyzer", layout="wide")
    st.title("Baseball Pitching Timing Analyzer")

    with st.form("analysis_form"):
        video_path = st.text_input("Local video path", value="videos/IMG_1322.MOV")
        throwing_hand = st.selectbox("Throwing hand", options=["right", "left"])

        time_columns = st.columns(2)
        start_time = time_columns[0].number_input(
            "Start time (seconds)",
            min_value=0.0,
            value=46.0,
            step=0.1,
        )
        end_time = time_columns[1].number_input(
            "End time (seconds)",
            min_value=0.0,
            value=48.0,
            step=0.1,
        )

        st.caption("Optional manual event frames. Leave blank to use auto detection.")
        frame_columns = st.columns(4)
        front_foot_strike_frame = frame_columns[0].text_input("Front foot strike frame")
        pelvis_peak_frame = frame_columns[1].text_input("Pelvis peak frame")
        trunk_peak_frame = frame_columns[2].text_input("Trunk peak frame")
        ball_release_frame = frame_columns[3].text_input("Ball release frame")

        st.caption("Search windows in milliseconds.")
        window_columns = st.columns(5)
        peak_search_start_ms = window_columns[0].number_input(
            "Peak search start",
            min_value=0.0,
            value=0.0,
            step=10.0,
        )
        pelvis_peak_search_end_ms = window_columns[1].number_input(
            "Pelvis search end",
            min_value=0.0,
            value=250.0,
            step=10.0,
        )
        trunk_peak_search_end_ms = window_columns[2].number_input(
            "Trunk search end",
            min_value=0.0,
            value=300.0,
            step=10.0,
        )
        ball_release_search_start_ms = window_columns[3].number_input(
            "Release search start",
            min_value=0.0,
            value=30.0,
            step=10.0,
        )
        ball_release_search_end_ms = window_columns[4].number_input(
            "Release search end",
            min_value=0.0,
            value=250.0,
            step=10.0,
        )

        output_prefix = st.text_input("Output prefix", value="streamlit_pitch")
        export_event_review = st.checkbox("Export event review frames", value=True)

        run_analysis = st.form_submit_button("Run Analysis")

    if not run_analysis:
        return

    try:
        options = {
            "video_path": video_path,
            "throwing_hand": throwing_hand,
            "start_time": start_time,
            "end_time": end_time,
            "front_foot_strike_frame": optional_int(front_foot_strike_frame),
            "pelvis_peak_frame": optional_int(pelvis_peak_frame),
            "trunk_peak_frame": optional_int(trunk_peak_frame),
            "ball_release_frame": optional_int(ball_release_frame),
            "peak_search_start_ms": peak_search_start_ms,
            "pelvis_peak_search_end_ms": pelvis_peak_search_end_ms,
            "trunk_peak_search_end_ms": trunk_peak_search_end_ms,
            "ball_release_search_start_ms": ball_release_search_start_ms,
            "ball_release_search_end_ms": ball_release_search_end_ms,
            "output_prefix": output_prefix.strip(),
            "export_event_review": export_event_review,
        }
    except ValueError as exc:
        st.error(f"Manual frame values must be integers. {exc}")
        return

    command = build_command(options)
    st.subheader("Command")
    st.code(shlex.join(command), language="bash")

    with st.spinner("Running local analysis..."):
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            cwd=Path(__file__).parent,
        )

    if result.stdout:
        st.text_area("Analyzer output", result.stdout, height=140)
    if result.stderr:
        st.text_area("Analyzer warnings/errors", result.stderr, height=140)

    if result.returncode != 0:
        st.error(f"Analysis failed with exit code {result.returncode}.")
        return

    st.success("Analysis complete.")
    display_outputs(options["output_prefix"])


if __name__ == "__main__":
    main()
