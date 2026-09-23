"""Unit tests for the pure signal helpers in analyze_pitch_timing.py."""

import math

import numpy as np
import pandas as pd
import pytest

apt = pytest.importorskip("analyze_pitch_timing")


def test_line_angle_degrees_cardinal_directions():
    assert apt.line_angle_degrees(0, 0, 1, 0) == pytest.approx(0.0)
    assert apt.line_angle_degrees(0, 0, 0, 1) == pytest.approx(90.0)  # image y points down
    assert apt.line_angle_degrees(0, 0, 0, -1) == pytest.approx(-90.0)
    assert abs(apt.line_angle_degrees(0, 0, -1, 0)) == pytest.approx(180.0)
    assert math.isnan(apt.line_angle_degrees(np.nan, 0, 1, 0))


def test_unwrap_removes_180_jump():
    raw = pd.Series([170.0, 179.0, -179.0, -170.0])
    unwrapped = apt.unwrap_angle_series_degrees(raw)
    assert np.all(np.diff(unwrapped.to_numpy()) > 0)
    assert unwrapped.iloc[-1] == pytest.approx(190.0)


def test_smooth_series_preserves_constant_and_length():
    series = pd.Series([5.0] * 9)
    smoothed = apt.smooth_series(series, 5)
    assert len(smoothed) == 9
    assert np.allclose(smoothed, 5.0)


def test_angular_velocity_of_linear_ramp_is_constant():
    fps = 240.0
    angles = pd.Series(np.arange(20) * 2.0)  # 2 degrees per frame
    velocity = apt.angular_velocity_degrees_per_second(angles, fps)
    assert np.allclose(velocity, 2.0 * fps)


def test_angular_velocity_handles_bad_input():
    assert apt.angular_velocity_degrees_per_second(pd.Series([1.0]), 30).isna().all()
    assert apt.angular_velocity_degrees_per_second(pd.Series([1.0, 2.0]), 0).isna().all()


def test_milliseconds_between_and_choose_event():
    assert apt.milliseconds_between(130, 100, 30.0) == pytest.approx(1000.0)
    assert apt.milliseconds_between(None, 100, 30.0) is None
    assert apt.choose_event(12, 40) == (12, "manual")
    assert apt.choose_event(None, 40) == (40, "auto")


def _synthetic_rotation_df(peak_frame, n=120, first_frame=1000, width=6.0):
    frames = np.arange(first_frame, first_frame + n)
    velocity = 900.0 * np.exp(-0.5 * ((frames - peak_frame) / width) ** 2)
    return pd.DataFrame(
        {
            "frame": frames,
            "hip_angle_smoothed": np.cumsum(velocity) / 240.0,
            "hip_angular_velocity": velocity,
        }
    )


def test_peak_in_frame_window_finds_true_peak():
    df = _synthetic_rotation_df(peak_frame=1060)
    assert apt.peak_in_frame_window(df, "hip_angular_velocity", 1000, 1119) == 1060
    # restricted window returns the window's own max
    assert apt.peak_in_frame_window(df, "hip_angular_velocity", 1000, 1050) == 1050
    assert apt.peak_in_frame_window(df, "hip_angular_velocity", None, 1050) is None


def test_detect_pelvis_peak_returns_onset_not_peak():
    """Documents current behavior: the 'pelvis peak' event is a rotation onset."""
    df = _synthetic_rotation_df(peak_frame=1060)
    result = apt.detect_pelvis_peak(df, 1000, 1119)
    assert result["frame"] < 1060
    # onset is where |velocity| first crosses max(120, 25% of max) while rising
    threshold = max(120.0, 0.25 * 900.0)
    first_cross = int(df.loc[df["hip_angular_velocity"] >= threshold, "frame"].iloc[0])
    assert result["frame"] == first_cross


def test_detector_version_is_semver():
    parts = apt.DETECTOR_VERSION.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)
