#!/usr/bin/env python3
"""
Local Streamlit UI for the baseball pitching analysis project.

The app stays local-only. It calls the command-line scripts with subprocess,
then displays the generated JSON reports, plots, and pose overlay videos.
"""

import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).parent.resolve()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def safe_output_prefix(video_path):
    """Create a filesystem-safe UI output prefix from video name and timestamp."""
    stem = Path(video_path).stem or "video"
    safe_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"ui_{safe_stem}_{timestamp}"


def output_path(output_prefix, filename):
    """Return an analyzer output path under outputs/."""
    if output_prefix:
        filename = f"{output_prefix}_{filename}"
    return OUTPUTS_DIR / filename


def optional_int(value):
    """Convert a text field to int, allowing blanks."""
    value = value.strip()
    if not value:
        return None
    return int(value)


def load_json(path):
    """Load JSON from disk."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def format_value(value, digits=2):
    """Format values for compact report tables."""
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return value


def report_table(title, report, fields):
    """Display selected report fields in a readable two-column table."""
    st.markdown(f"**{title}**")
    rows = [
        {"Metric": field, "Value": format_value(report.get(field))}
        for field in fields
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)


def build_auto_detect_command(
    video_path,
    throwing_hand,
    output_prefix,
    max_pitches,
    min_pitch_likeness,
):
    """Build the automatic pitch detection command."""
    return [
        sys.executable,
        "auto_detect_pitch_windows.py",
        video_path,
        "--throwing-hand",
        throwing_hand,
        "--output-prefix",
        output_prefix,
        "--max-windows",
        str(max_pitches),
        "--min-pitch-likeness",
        str(min_pitch_likeness),
        "--debug-candidates",
        "--run-analysis",
    ]


def build_manual_command(options):
    """Build the analyze_pitch_timing.py command from manual UI options."""
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


def build_pitch_manual_correction_command(
    video_path,
    throwing_hand,
    window,
    output_prefix,
    front_foot_strike_frame,
    pelvis_peak_frame,
    trunk_peak_frame,
    ball_release_frame,
):
    """Build a command to re-run one detected pitch with manual event frames."""
    return [
        sys.executable,
        "analyze_pitch_timing.py",
        video_path,
        "--throwing-hand",
        throwing_hand,
        "--start-time",
        str(window["start_time"]),
        "--end-time",
        str(window["end_time"]),
        "--front-foot-strike-frame",
        str(front_foot_strike_frame),
        "--pelvis-peak-frame",
        str(pelvis_peak_frame),
        "--trunk-peak-frame",
        str(trunk_peak_frame),
        "--ball-release-frame",
        str(ball_release_frame),
        "--output-prefix",
        output_prefix,
    ]


def run_command(command):
    """Run a local project command and return the subprocess result."""
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        cwd=PROJECT_ROOT,
    )


def display_run_log(result, use_expander=True, log_key=None):
    """Show subprocess stdout/stderr in an expander."""
    base_key = log_key or str(abs(hash(shlex.join(result.args))))

    def render_log():
        st.code(shlex.join(result.args), language="bash")
        if result.stdout:
            st.text_area("stdout", result.stdout, height=220, key=f"{base_key}_stdout")
        else:
            st.caption("No stdout.")
        if result.stderr:
            st.text_area("stderr", result.stderr, height=160, key=f"{base_key}_stderr")
        else:
            st.caption("No stderr.")

    if use_expander:
        with st.expander("Run log", expanded=False):
            render_log()
    else:
        st.markdown("**Run log**")
        render_log()


def display_fps_quality_warning(fps):
    """Show a simple frame-rate quality warning for timing analysis."""
    if fps is None:
        return
    try:
        fps_value = float(fps)
    except (TypeError, ValueError):
        return

    if fps_value < 60:
        st.warning(
            "This video is below 60 fps. Timing and release detection may be "
            "less reliable. Use 120-240 fps for better accuracy."
        )
    elif fps_value < 120:
        st.info(
            "This video is usable, but 120-240 fps is recommended for more "
            "precise event timing."
        )
    else:
        st.success("Good frame rate for timing analysis.")


def selected_pitch_windows(windows_report):
    """Return validated windows, falling back to all windows for older reports."""
    windows = windows_report.get("windows", [])
    if not windows:
        return []
    if any("validation_passed" in window for window in windows):
        return [window for window in windows if window.get("validation_passed") is True]
    return windows


def display_auto_detection_summary(prefix, min_pitch_likeness, max_pitches):
    """Display detected pitch windows from the auto detector JSON."""
    windows_path = output_path(prefix, "pitch_windows.json")
    if not windows_path.exists():
        st.warning(f"Pitch windows JSON not found: {windows_path}")
        return None

    windows_report = load_json(windows_path)
    selected_windows = selected_pitch_windows(windows_report)

    st.subheader("Auto Detection Summary")
    summary_columns = st.columns(5)
    summary_columns[0].metric("Selected pitches", len(selected_windows))
    summary_columns[1].metric("FPS", format_value(windows_report.get("fps")))
    summary_columns[2].metric(
        "Duration (s)",
        format_value(windows_report.get("duration_seconds")),
    )
    summary_columns[3].metric("Min pitch likeness", format_value(min_pitch_likeness))
    summary_columns[4].metric("Max pitches", max_pitches)
    display_fps_quality_warning(windows_report.get("fps"))

    if selected_windows:
        rows = []
        for window in selected_windows:
            rows.append(
                {
                    "window_id": window.get("window_id"),
                    "start_time": format_value(window.get("start_time")),
                    "end_time": format_value(window.get("end_time")),
                    "candidate_peak_time": format_value(
                        window.get("candidate_peak_time")
                    ),
                    "confidence": window.get("confidence", "N/A"),
                    "pitch_likeness_score": format_value(
                        window.get("pitch_likeness_score")
                    ),
                    "activity_score": format_value(window.get("activity_score")),
                    "mean_visibility": format_value(window.get("mean_visibility")),
                    "wrist_burst_clarity": format_value(
                        window.get("wrist_burst_clarity")
                    ),
                    "debug_reason": window.get("debug_reason", ""),
                }
            )
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    else:
        st.warning(
            "No validated pitch windows found. Try lowering min pitch likeness "
            "or using a clearer video."
        )

    return windows_report


def display_rejected_debug_candidates(prefix):
    """Display rejected/high-activity candidates from the debug CSV."""
    debug_path = output_path(prefix, "pitch_window_candidates.csv")
    with st.expander("Rejected / debug candidates", expanded=False):
        if not debug_path.exists():
            st.info("No debug candidate CSV found.")
            return

        candidates = pd.read_csv(debug_path)
        if candidates.empty:
            st.info("Debug candidate CSV is empty.")
            return

        rejected_mask = pd.Series(False, index=candidates.index)
        if "validation_passed" in candidates.columns:
            rejected_mask = rejected_mask | (candidates["validation_passed"] == False)
        if "selected_window" in candidates.columns:
            rejected_mask = rejected_mask | (candidates["selected_window"] == False)
        rejected = candidates[rejected_mask].copy() if rejected_mask.any() else candidates.copy()

        if rejected.empty:
            st.info("No rejected candidates found.")
            return

        def candidate_column(*names):
            for name in names:
                if name in rejected.columns:
                    return rejected[name]
            return pd.Series(["N/A"] * len(rejected), index=rejected.index)

        display = pd.DataFrame(
            {
                "time": candidate_column("time", "candidate_peak_time"),
                "smoothed_score": candidate_column("smoothed_score", "activity_score"),
                "pitch_likeness_score": candidate_column("pitch_likeness_score"),
                "validation_passed": candidate_column("validation_passed"),
                "rejection_reason": candidate_column("rejection_reason"),
                "wrist_speed": candidate_column("wrist_speed", "wrist_speed_peak"),
                "rotation_activity": candidate_column(
                    "rotation_activity",
                    "rotation_activity_peak",
                ),
                "visibility": candidate_column("visibility", "mean_visibility"),
            }
        )
        st.dataframe(display, hide_index=True, use_container_width=True)


def display_analysis_summary(report):
    """Show rule-based interpretation text and warnings."""
    st.markdown("**Analysis Summary**")
    sequence_classification = report.get("sequence_classification")
    if sequence_classification == "pelvis_then_trunk":
        st.success("Pelvis-to-trunk sequence looks clear in this 2D video.")
    elif sequence_classification == "pelvis_trunk_near_simultaneous":
        st.info(
            "Pelvis and trunk peaks are very close. This may indicate limited "
            "hip-shoulder separation or early trunk rotation, but confirm visually."
        )
    elif sequence_classification == "trunk_before_pelvis":
        st.warning(
            "Trunk appears to peak before pelvis. This may indicate early trunk "
            "rotation or sequencing issue."
        )
    else:
        st.info(report.get("sequence_result", "Sequence classification unavailable."))

    ball_release_confidence = report.get("ball_release_confidence")
    if isinstance(ball_release_confidence, (int, float)) and ball_release_confidence < 0.5:
        st.warning("Ball release was detected with low confidence. Confirm release frame visually.")

    arm_warning = report.get("throwing_arm_quality_warning")
    if arm_warning and arm_warning != "No major 2D throwing arm quality warning.":
        st.warning(arm_warning)

    sep_warning = report.get("hip_shoulder_separation_quality_warning")
    if sep_warning and sep_warning != "No major 2D separation quality warning.":
        st.warning(sep_warning)


def build_pitch_report(report: dict) -> list[str]:
    """Build a readable local-only coach-style report from timing_report.json."""
    lines = []
    sequence_classification = report.get("sequence_classification")
    sequence_result = report.get("sequence_result") or "Sequence result unavailable."
    sequence_issue = report.get("sequence_issue")
    sequence_note = report.get("sequence_confidence_note")
    pelvis_trunk_gap_ms = report.get("pelvis_trunk_peak_gap_ms")
    ball_release_confidence = report.get("ball_release_confidence")
    separation_interpretation = report.get(
        "hip_shoulder_separation_timing_interpretation"
    )
    separation_warning = report.get("hip_shoulder_separation_quality_warning")
    arm_warning = report.get("throwing_arm_quality_warning")

    lines.append("Overall summary")
    if sequence_classification == "pelvis_then_trunk":
        lines.append(
            "- The pelvis-to-trunk sequence appears clear in this 2D video."
        )
    elif sequence_classification == "pelvis_trunk_near_simultaneous":
        lines.append(
            "- Pelvis and trunk peaks are very close together. Treat the order as "
            "low-confidence and confirm it visually."
        )
    elif sequence_classification == "trunk_before_pelvis":
        lines.append(
            "- Trunk rotation appears to peak before pelvis rotation. This may be "
            "a sequencing issue, but it should be confirmed on the overlay."
        )
    else:
        lines.append(
            "- The event order is not clear enough for a strong sequence read."
        )
    lines.append(
        "- This report is based on single-camera 2D pose landmarks, so it should "
        "be used as a review aid rather than a full biomechanics assessment."
    )
    lines.append("")

    lines.append("Sequence")
    lines.append(f"- Result: {sequence_result}")
    if pelvis_trunk_gap_ms is not None:
        lines.append(
            f"- Pelvis-to-trunk peak gap: {format_value(pelvis_trunk_gap_ms)} ms."
        )
    if sequence_issue:
        lines.append(f"- Possible issue: {sequence_issue}")
    if sequence_note:
        lines.append(f"- Confidence note: {sequence_note}")
    lines.append("")

    lines.append("Hip-shoulder separation")
    delivery_sep = report.get(
        "max_hip_shoulder_separation_directional_delivery_window"
    )
    stretch_sep = report.get("max_hip_shoulder_separation_directional_stretch_phase")
    if delivery_sep is not None:
        lines.append(
            "- Max delivery-window 2D directional separation proxy: "
            f"{format_value(delivery_sep)} deg."
        )
    if stretch_sep is not None:
        lines.append(
            "- Max stretch-phase 2D directional separation proxy: "
            f"{format_value(stretch_sep)} deg."
        )
    if separation_interpretation:
        lines.append(f"- Interpretation: {separation_interpretation}")
    lines.append(
        "- Separation is a camera-view 2D proxy from shoulder-line and hip-line "
        "angles, not true 3D torso-pelvis separation."
    )
    lines.append("")

    lines.append("Arm slot / throwing arm")
    forearm_vertical = report.get("forearm_angle_vs_vertical_at_ball_release")
    arm_slot_vertical = report.get("arm_slot_proxy_vs_vertical_at_ball_release")
    max_layback_proxy_abs = report.get("max_layback_proxy_abs")
    if forearm_vertical is not None:
        lines.append(
            "- Forearm angle vs vertical at approximate ball release: "
            f"{format_value(forearm_vertical)} deg."
        )
    if arm_slot_vertical is not None:
        lines.append(
            "- 2D arm slot proxy vs vertical at approximate ball release: "
            f"{format_value(arm_slot_vertical)} deg."
        )
    if max_layback_proxy_abs is not None:
        lines.append(
            "- Max 2D layback-related proxy magnitude: "
            f"{format_value(max_layback_proxy_abs)} deg."
        )
    lines.append(
        "- Arm slot and layback-related values are 2D camera-view proxies. They "
        "are not true 3D arm slot, true shoulder external rotation, or elbow force."
    )
    lines.append("")

    lines.append("Confidence and warnings")
    warnings = []
    if isinstance(ball_release_confidence, (int, float)):
        lines.append(
            f"- Ball release confidence: {format_value(ball_release_confidence)}."
        )
        if ball_release_confidence < 0.5:
            warnings.append(
                "Ball release confidence is low; confirm the release frame visually."
            )
    if separation_warning and separation_warning != "No major 2D separation quality warning.":
        warnings.append(separation_warning)
    if arm_warning and arm_warning != "No major 2D throwing arm quality warning.":
        warnings.append(arm_warning)
    if warnings:
        for warning in warnings:
            lines.append(f"- Warning: {warning}")
    else:
        lines.append("- No major quality warnings were reported.")
    lines.append("")

    lines.append("Suggested focus")
    focus_items = []
    if sequence_classification == "pelvis_trunk_near_simultaneous":
        focus_items.append(
            "Review whether trunk rotation is starting too close to pelvis peak."
        )
    elif sequence_classification == "trunk_before_pelvis":
        focus_items.append(
            "Review sequencing and whether the trunk is opening early."
        )
    elif sequence_classification == "pelvis_then_trunk":
        focus_items.append(
            "Use the overlay to confirm that the clear pelvis-to-trunk order matches the visual delivery."
        )
    else:
        focus_items.append(
            "Confirm key event frames manually before drawing conclusions."
        )
    if isinstance(ball_release_confidence, (int, float)) and ball_release_confidence < 0.5:
        focus_items.append("Manually verify the approximate ball release frame.")
    if separation_warning and separation_warning != "No major 2D separation quality warning.":
        focus_items.append("Use the separation trend cautiously because 2D angle quality may be noisy.")
    if arm_warning and arm_warning != "No major 2D throwing arm quality warning.":
        focus_items.append("Check shoulder, elbow, and wrist landmark visibility on the overlay.")
    for item in focus_items:
        lines.append(f"- {item}")

    return lines


def display_coach_style_report(report, download_key):
    """Display and offer a download for the coach-style text report."""
    lines = build_pitch_report(report)
    report_text = "\n".join(lines)
    st.markdown("**Coach-style Report**")
    st.text(report_text)
    st.download_button(
        "Download report as .txt",
        data=report_text,
        file_name=f"{download_key}_coach_report.txt",
        mime="text/plain",
        key=f"{download_key}_download_report",
    )


def display_corrected_analysis(output_prefix):
    """Display outputs from a manual-corrected pitch analysis."""
    report_path = output_path(output_prefix, "timing_report.json")
    overlay_path = output_path(output_prefix, "pose_overlay.mp4")
    plot_path = output_path(output_prefix, "angles_plot.png")

    st.markdown("**Manual-corrected analysis**")
    media_columns = st.columns(2)
    with media_columns[0]:
        st.markdown("Pose Overlay")
        if overlay_path.exists():
            st.video(str(overlay_path))
        else:
            st.error(f"Manual corrected pose overlay not found: {overlay_path}")
    with media_columns[1]:
        st.markdown("Angles Plot")
        if plot_path.exists():
            st.image(str(plot_path))
        else:
            st.error(f"Manual corrected angles plot not found: {plot_path}")

    if not report_path.exists():
        st.error(f"Manual corrected timing report not found: {report_path}")
        return

    report = load_json(report_path)
    display_analysis_summary(report)
    display_coach_style_report(report, f"{output_prefix}_manual")
    report_table(
        "Manual-Corrected Timing",
        report,
        [
            "front_foot_strike_frame",
            "pelvis_peak_frame",
            "trunk_peak_frame",
            "ball_release_frame",
            "detected_sequence_order",
            "sequence_classification",
            "sequence_result",
            "sequence_issue",
            "sequence_confidence_note",
        ],
    )
    with st.expander("Manual corrected raw timing report JSON"):
        st.json(report)


def display_manual_event_correction(prefix, window, report, video_path, throwing_hand):
    """Render per-pitch manual event correction controls."""
    window_id = window.get("window_id")
    corrected_prefix = f"{prefix}_window_{window_id}_manual"
    with st.expander("Manual event correction", expanded=False):
        st.caption("Adjust event frames after visually reviewing the pose overlay.")
        columns = st.columns(4)
        front_foot_strike_frame = columns[0].number_input(
            "Front foot strike frame",
            min_value=0,
            value=int(report.get("front_foot_strike_frame") or 0),
            step=1,
            key=f"{prefix}_{window_id}_manual_ffs",
        )
        pelvis_peak_frame = columns[1].number_input(
            "Pelvis peak frame",
            min_value=0,
            value=int(report.get("pelvis_peak_frame") or 0),
            step=1,
            key=f"{prefix}_{window_id}_manual_pelvis",
        )
        trunk_peak_frame = columns[2].number_input(
            "Trunk peak frame",
            min_value=0,
            value=int(report.get("trunk_peak_frame") or 0),
            step=1,
            key=f"{prefix}_{window_id}_manual_trunk",
        )
        ball_release_frame = columns[3].number_input(
            "Ball release frame",
            min_value=0,
            value=int(report.get("ball_release_frame") or 0),
            step=1,
            key=f"{prefix}_{window_id}_manual_release",
        )

        if st.button(
            "Re-run this pitch with manual corrections",
            key=f"{prefix}_{window_id}_rerun_manual",
        ):
            command = build_pitch_manual_correction_command(
                video_path,
                throwing_hand,
                window,
                corrected_prefix,
                int(front_foot_strike_frame),
                int(pelvis_peak_frame),
                int(trunk_peak_frame),
                int(ball_release_frame),
            )
            with st.spinner("Running manual-corrected analysis for this pitch..."):
                result = run_command(command)

            display_run_log(
                result,
                use_expander=False,
                log_key=f"{prefix}_{window_id}_manual_log",
            )
            if result.returncode != 0:
                st.error(
                    f"Manual-corrected analysis failed with exit code {result.returncode}."
                )
                return
            st.success("Manual-corrected analysis complete.")

    if output_path(corrected_prefix, "timing_report.json").exists():
        display_corrected_analysis(corrected_prefix)


def display_pitch_tab(prefix, window, video_path, throwing_hand):
    """Display video, plot, and readable timing report for one detected pitch."""
    window_id = window.get("window_id")
    pitch_prefix = f"{prefix}_window_{window_id}"
    report_path = output_path(pitch_prefix, "timing_report.json")
    overlay_path = output_path(pitch_prefix, "pose_overlay.mp4")
    plot_path = output_path(pitch_prefix, "angles_plot.png")

    st.markdown(
        f"Window: {format_value(window.get('start_time'))}s to "
        f"{format_value(window.get('end_time'))}s"
    )

    window_fields = [
        "start_time",
        "end_time",
        "candidate_peak_time",
        "confidence",
        "pitch_likeness_score",
        "activity_score",
        "mean_visibility",
        "wrist_burst_clarity",
        "debug_reason",
    ]
    report_table("Detection Details", window, window_fields)

    media_columns = st.columns(2)
    with media_columns[0]:
        st.markdown("**Pose Overlay**")
        if overlay_path.exists():
            st.video(str(overlay_path))
        else:
            st.warning(f"Pose overlay video not found: {overlay_path}")

    with media_columns[1]:
        st.markdown("**Angles Plot**")
        if plot_path.exists():
            st.image(str(plot_path))
        else:
            st.warning(f"Angles plot not found: {plot_path}")

    if not report_path.exists():
        st.warning(f"Timing report not found: {report_path}")
        return

    report = load_json(report_path)
    st.markdown("**Automatic analysis**")
    display_analysis_summary(report)

    timing_fields = [
        "front_foot_strike_frame",
        "pelvis_peak_frame",
        "trunk_peak_frame",
        "ball_release_frame",
        "detected_sequence_order",
        "pelvis_trunk_peak_gap_frames",
        "pelvis_trunk_peak_gap_ms",
        "sequence_classification",
        "sequence_result",
        "sequence_issue",
        "sequence_confidence_note",
    ]
    separation_fields = [
        "pelvis_opening_direction",
        "max_hip_shoulder_separation_directional_delivery_window",
        "max_hip_shoulder_separation_directional_delivery_window_frame",
        "max_hip_shoulder_separation_directional_stretch_phase",
        "max_hip_shoulder_separation_directional_stretch_phase_frame",
        "hip_shoulder_separation_timing_interpretation",
        "hip_shoulder_separation_quality_warning",
    ]
    arm_fields = [
        "forearm_angle_vs_horizontal_at_ball_release",
        "forearm_angle_vs_vertical_at_ball_release",
        "arm_slot_proxy_vs_vertical_at_ball_release",
        "arm_slot_proxy_vs_horizontal_at_ball_release",
        "max_layback_proxy_abs",
        "max_layback_proxy_frame",
        "throwing_arm_quality_warning",
    ]

    report_columns = st.columns(3)
    with report_columns[0]:
        report_table("Timing", report, timing_fields)
    with report_columns[1]:
        report_table("Hip-Shoulder Separation", report, separation_fields)
    with report_columns[2]:
        report_table("Throwing Arm", report, arm_fields)

    display_coach_style_report(report, pitch_prefix)

    with st.expander("Raw timing report JSON"):
        st.json(report)

    display_manual_event_correction(prefix, window, report, video_path, throwing_hand)


def display_detected_pitch_tabs(prefix, windows_report):
    """Create one tab per detected pitch window."""
    windows = selected_pitch_windows(windows_report)
    if not windows:
        return

    tabs = st.tabs([f"Pitch {window.get('window_id')}" for window in windows])
    video_path = windows_report.get("video_path", "")
    throwing_hand = windows_report.get("throwing_hand", "right")
    for tab, window in zip(tabs, windows):
        with tab:
            display_pitch_tab(prefix, window, video_path, throwing_hand)


def display_manual_outputs(output_prefix):
    """Display outputs from manual single-window analysis."""
    report_path = output_path(output_prefix, "timing_report.json")
    plot_path = output_path(output_prefix, "angles_plot.png")
    overlay_path = output_path(output_prefix, "pose_overlay.mp4")

    if not report_path.exists():
        st.warning(f"Timing report not found: {report_path}")
        return

    report = load_json(report_path)
    display_analysis_summary(report)

    media_columns = st.columns(2)
    with media_columns[0]:
        if plot_path.exists():
            st.image(str(plot_path))
        else:
            st.warning(f"Angles plot not found: {plot_path}")
    with media_columns[1]:
        if overlay_path.exists():
            st.video(str(overlay_path))
        else:
            st.warning(f"Pose overlay video not found: {overlay_path}")

    with st.expander("Raw timing report JSON"):
        st.json(report)


def render_manual_single_window_analysis():
    """Keep the old manual start/end workflow for debugging."""
    with st.expander("Manual single-window analysis", expanded=False):
        with st.form("manual_analysis_form"):
            video_path = st.text_input(
                "Local video path",
                value="videos/IMG_1322.MOV",
                key="manual_video_path",
            )
            throwing_hand = st.selectbox(
                "Throwing hand",
                options=["right", "left"],
                key="manual_throwing_hand",
            )

            time_columns = st.columns(2)
            start_time = time_columns[0].number_input(
                "Start time (seconds)",
                min_value=0.0,
                value=46.0,
                step=0.1,
                key="manual_start_time",
            )
            end_time = time_columns[1].number_input(
                "End time (seconds)",
                min_value=0.0,
                value=48.0,
                step=0.1,
                key="manual_end_time",
            )

            st.caption("Optional manual event frames. Leave blank to use auto detection.")
            frame_columns = st.columns(4)
            front_foot_strike_frame = frame_columns[0].text_input(
                "Front foot strike frame",
                key="manual_ffs_frame",
            )
            pelvis_peak_frame = frame_columns[1].text_input(
                "Pelvis peak frame",
                key="manual_pelvis_frame",
            )
            trunk_peak_frame = frame_columns[2].text_input(
                "Trunk peak frame",
                key="manual_trunk_frame",
            )
            ball_release_frame = frame_columns[3].text_input(
                "Ball release frame",
                key="manual_release_frame",
            )

            st.caption("Search windows in milliseconds.")
            window_columns = st.columns(5)
            peak_search_start_ms = window_columns[0].number_input(
                "Peak search start",
                min_value=0.0,
                value=0.0,
                step=10.0,
                key="manual_peak_search_start_ms",
            )
            pelvis_peak_search_end_ms = window_columns[1].number_input(
                "Pelvis search end",
                min_value=0.0,
                value=250.0,
                step=10.0,
                key="manual_pelvis_search_end_ms",
            )
            trunk_peak_search_end_ms = window_columns[2].number_input(
                "Trunk search end",
                min_value=0.0,
                value=300.0,
                step=10.0,
                key="manual_trunk_search_end_ms",
            )
            ball_release_search_start_ms = window_columns[3].number_input(
                "Release search start",
                min_value=0.0,
                value=30.0,
                step=10.0,
                key="manual_release_search_start_ms",
            )
            ball_release_search_end_ms = window_columns[4].number_input(
                "Release search end",
                min_value=0.0,
                value=250.0,
                step=10.0,
                key="manual_release_search_end_ms",
            )

            output_prefix = st.text_input(
                "Output prefix",
                value="streamlit_pitch",
                key="manual_output_prefix",
            )
            export_event_review = st.checkbox(
                "Export event review frames",
                value=True,
                key="manual_export_event_review",
            )

            run_manual = st.form_submit_button("Run Manual Analysis")

        if not run_manual:
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

        command = build_manual_command(options)
        with st.spinner("Running local single-window analysis..."):
            result = run_command(command)
        display_run_log(result)

        if result.returncode != 0:
            st.error(f"Analysis failed with exit code {result.returncode}.")
            return

        st.success("Manual analysis complete.")
        display_manual_outputs(options["output_prefix"])


def main():
    """Render the Streamlit app."""
    st.set_page_config(page_title="Baseball Pitching Analysis", layout="wide")
    st.title("Baseball Pitching Analysis")

    with st.sidebar:
        st.header("Auto Analysis")
        video_path = st.text_input("Video path", value="videos/test_pitch.MP4")
        throwing_hand = st.selectbox("Throwing hand", options=["right", "left"])
        max_pitches = st.number_input(
            "Max pitches",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )
        min_pitch_likeness = st.slider(
            "Minimum pitch likeness",
            min_value=0.0,
            max_value=1.0,
            value=0.75,
            step=0.05,
        )
        show_rejected_candidates = st.checkbox(
            "Show rejected candidates / debug info",
            value=False,
        )
        run_auto = st.button("Auto Detect & Analyze Pitches", type="primary")

    if run_auto:
        prefix = safe_output_prefix(video_path)
        command = build_auto_detect_command(
            video_path,
            throwing_hand,
            prefix,
            int(max_pitches),
            float(min_pitch_likeness),
        )

        with st.spinner("Detecting pitch windows and running local analysis..."):
            result = run_command(command)

        display_run_log(result)
        if result.returncode != 0:
            st.error(f"Auto detection failed with exit code {result.returncode}.")
        else:
            st.session_state["last_auto_prefix"] = prefix
            st.session_state["last_auto_command"] = command
            st.session_state["last_auto_min_pitch_likeness"] = float(min_pitch_likeness)
            st.session_state["last_auto_max_pitches"] = int(max_pitches)
            st.success("Auto detection and analysis complete.")
            windows_report = display_auto_detection_summary(
                prefix,
                float(min_pitch_likeness),
                int(max_pitches),
            )
            if windows_report:
                display_detected_pitch_tabs(prefix, windows_report)
            if show_rejected_candidates:
                display_rejected_debug_candidates(prefix)
    elif st.session_state.get("last_auto_prefix"):
        prefix = st.session_state["last_auto_prefix"]
        last_min_pitch_likeness = st.session_state.get(
            "last_auto_min_pitch_likeness",
            min_pitch_likeness,
        )
        last_max_pitches = st.session_state.get("last_auto_max_pitches", max_pitches)
        st.info(f"Showing last auto analysis: {prefix}")
        windows_report = display_auto_detection_summary(
            prefix,
            last_min_pitch_likeness,
            last_max_pitches,
        )
        if windows_report:
            display_detected_pitch_tabs(prefix, windows_report)
        if show_rejected_candidates:
            display_rejected_debug_candidates(prefix)
    else:
        st.info("Choose a local video and click Auto Detect & Analyze Pitches.")

    render_manual_single_window_analysis()


if __name__ == "__main__":
    main()
