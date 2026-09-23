#!/usr/bin/env python3
"""
Lab-data simulation (RQ2/RQ3): how well can single-camera 2D proxies recover
pitching event timing?

For every OpenBiomechanics (OBP) pitch, the 3D joint centers (360 Hz) are
projected into a virtual camera, resampled to phone frame rates, optionally
perturbed with landmark noise, converted into the same landmark table the
MediaPipe pipeline produces, and passed through the SAME detector functions in
analyze_pitch_timing.py. Detected events are compared with lab ground truth:

- front foot strike  vs fp_10_time (10% bodyweight on the force plate)
- ball release       vs BR_time
- pelvis / trunk     vs argmax of pelvis_velo_z / torso_velo_z between
                        fp_10_time and BR_time (joint_velos.csv)

It also evaluates an idealized pseudo-3D proxy: the rotation angle of the hip
and shoulder lines in the horizontal (ground) plane, computed from the true 3D
joint centers. This is the upper bound for any world-landmark approach (RQ3).

Camera azimuth convention (degrees, relative to the pitcher's handedness):
0 = behind the pitcher looking toward home, 90 = throwing-arm side,
180 = in front (from home plate), 270 = glove side. The camera is horizontal
and orthographic. Image coordinates are MediaPipe-style normalized [0, 1] with
y pointing down; the body occupies --body-frame-fraction of the frame height,
and --aspect sets frame width/height (16/9 landscape by default).

No MediaPipe inference or video I/O is involved, so results are identical on
any platform. See docs/RESEARCH_GUIDE.md, Phase 4.
"""

import argparse
import json
import os
import sys
import time
import zlib
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import analyze_pitch_timing as analyzer  # noqa: E402

OBP_TO_MEDIAPIPE_RIGHT_HANDED = {
    "right_shoulder": "shoulder_jc",
    "left_shoulder": "glove_shoulder_jc",
    "right_hip": "rear_hip",
    "left_hip": "lead_hip",
    "right_ankle": "rear_ankle_jc",
    "left_ankle": "lead_ankle_jc",
    "right_elbow": "elbow_jc",
    "left_elbow": "glove_elbow_jc",
    "right_wrist": "wrist_jc",
    "left_wrist": "glove_wrist_jc",
}

SMOOTHING_WINDOW = 5
PEAK_SEARCH = {  # analyzer defaults (ms)
    "peak_start_ms": 0.0,
    "pelvis_end_ms": 300.0,
    "trunk_end_ms": 350.0,
    "release_start_ms": 30.0,
    "release_end_ms": 250.0,
}
FRAME_OFFSET = 1000  # synthetic original-video frame numbers start here


def obp_mapping(throwing_hand):
    """Map MediaPipe landmark names to OBP joint-center prefixes."""
    if throwing_hand == "right":
        return dict(OBP_TO_MEDIAPIPE_RIGHT_HANDED)
    swap = {"left": "right", "right": "left"}
    return {
        f"{swap[name.split('_', 1)[0]]}_{name.split('_', 1)[1]}": obp
        for name, obp in OBP_TO_MEDIAPIPE_RIGHT_HANDED.items()
    }


def arm_side_y_sign(throwing_hand):
    """OBP lab frame: +y points toward first base. Verified 2026-09-23 from
    ball-release frames: the throwing shoulder is at -y for right-handers and
    +y for left-handers."""
    return -1.0 if throwing_hand == "right" else 1.0


def camera_axes(azimuth_deg, throwing_hand):
    """Return (right, up) unit vectors of a horizontal camera at an azimuth."""
    theta = np.deg2rad(azimuth_deg)
    s = arm_side_y_sign(throwing_hand)
    position = np.array([-np.cos(theta), s * np.sin(theta), 0.0])
    forward = -position
    up = np.array([0.0, 0.0, 1.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    return right, up


def load_obp(obp_dir):
    """Load OBP tables and return one dict per pitch with numpy arrays."""
    obp_dir = Path(obp_dir)
    landmarks = pd.read_csv(obp_dir / "landmarks.csv")
    velos = pd.read_csv(
        obp_dir / "joint_velos.csv",
        usecols=["session_pitch", "time", "pelvis_velo_z", "torso_velo_z"],
    )
    poi = pd.read_csv(obp_dir / "poi_metrics.csv", usecols=["session_pitch", "p_throws", "pitch_speed_mph"])
    meta = pd.read_csv(obp_dir / "metadata.csv", usecols=["session_pitch", "user", "session_height_m", "playing_level"])
    for frame in (landmarks, velos, poi, meta):
        frame["session_pitch"] = frame["session_pitch"].astype(str)
    info = poi.merge(meta, on="session_pitch", how="inner").set_index("session_pitch")
    velo_groups = dict(tuple(velos.groupby("session_pitch")))

    pitches = []
    skipped = {"missing_info": 0, "missing_events": 0, "missing_velos": 0}
    for session_pitch, group in landmarks.groupby("session_pitch"):
        if session_pitch not in info.index:
            skipped["missing_info"] += 1
            continue
        fp = float(group["fp_10_time"].iloc[0])
        br = float(group["BR_time"].iloc[0])
        if not (np.isfinite(fp) and np.isfinite(br) and br > fp):
            skipped["missing_events"] += 1
            continue
        velo = velo_groups.get(session_pitch)
        if velo is None:
            skipped["missing_velos"] += 1
            continue
        window = (velo["time"] >= fp) & (velo["time"] <= br)
        if window.sum() < 3:
            skipped["missing_velos"] += 1
            continue
        vt = velo.loc[window, "time"].to_numpy()
        row = info.loc[session_pitch]
        hand = "right" if row["p_throws"] == "R" else "left"
        joints = {}
        for obp_name in set(OBP_TO_MEDIAPIPE_RIGHT_HANDED.values()):
            joints[obp_name] = group[[f"{obp_name}_{a}" for a in "xyz"]].to_numpy(dtype=float)
        pitches.append(
            {
                "session_pitch": session_pitch,
                "user": int(row["user"]),
                "playing_level": row["playing_level"],
                "pitch_speed_mph": float(row["pitch_speed_mph"]),
                "throwing_hand": hand,
                "height_m": float(row["session_height_m"]),
                "time": group["time"].to_numpy(dtype=float),
                "joints": joints,
                "fp_time": fp,
                "br_time": br,
                "pelvis_peak_time": float(vt[np.argmax(velo.loc[window, "pelvis_velo_z"].to_numpy())]),
                "trunk_peak_time": float(vt[np.argmax(velo.loc[window, "torso_velo_z"].to_numpy())]),
            }
        )
    return pitches, skipped


def resample_joints(pitch, fps, phase):
    """Linearly interpolate every joint onto a frame grid starting at +phase."""
    t = pitch["time"]
    grid = np.arange(t[0] + phase, t[-1], 1.0 / fps)
    joints = {
        name: np.column_stack([np.interp(grid, t, xyz[:, k]) for k in range(3)])
        for name, xyz in pitch["joints"].items()
    }
    return grid, joints


def project_to_landmark_table(pitch, grid, joints, azimuth_deg, fps, noise_body_frac,
                              rng, body_frame_fraction, aspect):
    """Build the analyzer's landmark DataFrame from resampled 3D joints."""
    right, up = camera_axes(azimuth_deg, pitch["throwing_hand"])
    center = 0.5 * (joints["rear_hip"] + joints["lead_hip"]).mean(axis=0)
    scale_y = body_frame_fraction / pitch["height_m"]   # normalized units per meter (vertical)
    scale_x = scale_y / aspect                           # frame is wider than tall
    frames = np.arange(len(grid)) + FRAME_OFFSET
    table = {
        "processed_frame": np.arange(len(grid)),
        "frame": frames,
        "time_seconds": frames / fps,
        "processed_time_seconds": np.arange(len(grid)) / fps,
        "pose_detected": np.ones(len(grid), dtype=bool),
    }
    for mp_name, obp_name in obp_mapping(pitch["throwing_hand"]).items():
        rel = joints[obp_name] - center
        x = 0.5 + scale_x * (rel @ right)
        y = 0.5 - scale_y * (rel @ up)
        if noise_body_frac > 0:
            sigma_y = noise_body_frac * body_frame_fraction
            x = x + rng.normal(0.0, sigma_y / aspect, size=len(x))
            y = y + rng.normal(0.0, sigma_y, size=len(y))
        table[f"{mp_name}_x"] = x
        table[f"{mp_name}_y"] = y
        table[f"{mp_name}_visibility"] = np.ones(len(grid))
    return pd.DataFrame(table)


def frame_to_grid_time(frame, grid):
    if frame is None or (isinstance(frame, float) and not np.isfinite(frame)):
        return np.nan
    index = int(frame) - FRAME_OFFSET
    if 0 <= index < len(grid):
        return float(grid[index])
    return np.nan


def nearest_frame(time_value, grid):
    return int(np.argmin(np.abs(grid - time_value))) + FRAME_OFFSET


def run_detectors(df, fps, hand, ffs_frame=None):
    """Run analyzer event functions. If ffs_frame is given, it replaces the
    automatic FFS (oracle mode) so proxy error is isolated from FFS error."""
    out = {}
    if ffs_frame is None:
        ffs_frame = analyzer.detect_front_foot_strike(df, hand, fps).get("frame")
    out["ffs"] = ffs_frame
    if ffs_frame is None:
        return {**out, "pelvis_onset": None, "pelvis_peakvel": None, "trunk": None, "br": None}
    p0, p1 = analyzer.peak_search_window_frames(ffs_frame, fps, PEAK_SEARCH["peak_start_ms"], PEAK_SEARCH["pelvis_end_ms"])
    t0, t1 = analyzer.peak_search_window_frames(ffs_frame, fps, PEAK_SEARCH["peak_start_ms"], PEAK_SEARCH["trunk_end_ms"])
    out["pelvis_onset"] = analyzer.detect_pelvis_peak(df, p0, p1).get("frame")
    out["pelvis_peakvel"] = analyzer.peak_in_frame_window(df, "hip_angular_velocity", p0, p1)
    out["trunk"] = analyzer.peak_in_frame_window(df, "shoulder_angular_velocity", t0, t1)
    out["br"] = None
    if out["trunk"] is not None:
        out["br"] = analyzer.detect_ball_release(
            df, hand, out["trunk"], fps, PEAK_SEARCH["release_start_ms"], PEAK_SEARCH["release_end_ms"]
        ).get("frame")
    return out


def horizontal_plane_peak_time(joints, grid, fps, a_name, b_name, t_start, t_end):
    """Idealized pseudo-3D proxy: peak |d/dt| of the segment's ground-plane angle."""
    vector = joints[a_name] - joints[b_name]
    angle = pd.Series(np.degrees(np.unwrap(np.arctan2(vector[:, 1], vector[:, 0]))))
    angle = analyzer.smooth_series(angle, SMOOTHING_WINDOW)
    velocity = np.abs(np.gradient(angle.to_numpy()) * fps)
    mask = (grid >= t_start) & (grid <= t_end)
    if mask.sum() < 1:
        return np.nan
    return float(grid[mask][np.argmax(velocity[mask])])


def ms(a, b):
    return (a - b) * 1000.0 if np.isfinite(a) and np.isfinite(b) else np.nan


def simulate_one(pitch, azimuth, fps, noise, seed, body_frame_fraction, aspect):
    rng = np.random.default_rng(
        [seed, int(azimuth * 10), int(fps), int(noise * 1e5), zlib.crc32(pitch["session_pitch"].encode())]
    )
    grid, joints = resample_joints(pitch, fps, rng.uniform(0.0, 1.0 / fps))
    raw = project_to_landmark_table(pitch, grid, joints, azimuth, fps, noise, rng, body_frame_fraction, aspect)
    hand = pitch["throwing_hand"]
    df = analyzer.add_calculations(raw, fps, SMOOTHING_WINDOW, hand)

    auto = run_detectors(df, fps, hand)
    oracle = run_detectors(df, fps, hand, ffs_frame=nearest_frame(pitch["fp_time"], grid))
    t = {k: frame_to_grid_time(v, grid) for k, v in auto.items()}
    to = {k: frame_to_grid_time(v, grid) for k, v in oracle.items()}

    true_p, true_t = pitch["pelvis_peak_time"], pitch["trunk_peak_time"]
    fp, br = pitch["fp_time"], pitch["br_time"]
    top_p = horizontal_plane_peak_time(joints, grid, fps, "lead_hip", "rear_hip", fp, br)
    top_t = horizontal_plane_peak_time(joints, grid, fps, "glove_shoulder_jc", "shoulder_jc", fp, br)

    def order_ok(p_time, t_time):
        if not (np.isfinite(p_time) and np.isfinite(t_time)):
            return np.nan
        return float(np.sign(t_time - p_time) == np.sign(true_t - true_p))

    return {
        "session_pitch": pitch["session_pitch"],
        "user": pitch["user"],
        "throwing_hand": hand,
        "azimuth_deg": azimuth,
        "fps": fps,
        "noise_body_frac": noise,
        "seed": seed,
        "true_gap_ms": ms(true_t, true_p),
        "ffs_err_ms": ms(t["ffs"], fp),
        "br_err_ms": ms(t["br"], br),
        "pelvis_onset_err_ms": ms(t["pelvis_onset"], true_p),
        "pelvis_peakvel_err_ms": ms(t["pelvis_peakvel"], true_p),
        "trunk_err_ms": ms(t["trunk"], true_t),
        "oracle_pelvis_onset_err_ms": ms(to["pelvis_onset"], true_p),
        "oracle_pelvis_peakvel_err_ms": ms(to["pelvis_peakvel"], true_p),
        "oracle_trunk_err_ms": ms(to["trunk"], true_t),
        "oracle_br_err_ms": ms(to["br"], br),
        "top_pelvis_err_ms": ms(top_p, true_p),
        "top_trunk_err_ms": ms(top_t, true_t),
        "order_ok_current_rule": order_ok(t["pelvis_onset"], t["trunk"]),
        "order_ok_peakvel": order_ok(t["pelvis_peakvel"], t["trunk"]),
        "order_ok_oracle_peakvel": order_ok(to["pelvis_peakvel"], to["trunk"]),
        "order_ok_top": order_ok(top_p, top_t),
        "detected_gap_current_rule_ms": ms(t["trunk"], t["pelvis_onset"]),
        "detected_gap_peakvel_ms": ms(t["trunk"], t["pelvis_peakvel"]),
    }


_PITCHES = None


def _init(pitches):
    global _PITCHES
    _PITCHES = pitches


def _work(job):
    index, azimuth, fps, noise, seed, frac, aspect = job
    try:
        return simulate_one(_PITCHES[index], azimuth, fps, noise, seed, frac, aspect)
    except Exception as error:  # keep the sweep running; record the failure
        return {"session_pitch": _PITCHES[index]["session_pitch"], "azimuth_deg": azimuth, "fps": fps,
                "noise_body_frac": noise, "seed": seed, "error": repr(error)}


def parse_list(text, cast=float):
    return [cast(item) for item in str(text).split(",") if item.strip()]


def parse_args():
    parser = argparse.ArgumentParser(description="OBP single-camera simulation (RQ2/RQ3).")
    parser.add_argument("--obp-dir", default="data/external/obp")
    parser.add_argument("--azimuths", default="0,30,60,90,120,150,180,210,240,270,300,330")
    parser.add_argument("--fps", default="30,60,120,240")
    parser.add_argument("--noise", default="0", help="Landmark noise SD as a fraction of body height.")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--body-frame-fraction", type=float, default=0.5)
    parser.add_argument("--aspect", type=float, default=16 / 9)
    parser.add_argument("--limit", type=int, default=None, help="Use only the first N pitches (smoke test).")
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 0))
    parser.add_argument("--output", default="outputs/rq2_sim.csv")
    parser.add_argument("--shard", type=int, default=0, help="Run only jobs[shard::num_shards].")
    parser.add_argument("--num-shards", type=int, default=1,
                        help="Split the sweep into shards (e.g. for shells with a time limit). "
                             "Each shard writes <output>.shardK-of-N.csv; research/obp_summary.py merges them.")
    return parser.parse_args()


def main():
    args = parse_args()
    started = time.time()
    pitches, skipped = load_obp(args.obp_dir)
    pitches.sort(key=lambda p: p["session_pitch"])
    if args.limit:
        pitches = pitches[: args.limit]
    jobs = [
        (i, az, fps, noise, seed, args.body_frame_fraction, args.aspect)
        for i in range(len(pitches))
        for az in parse_list(args.azimuths)
        for fps in parse_list(args.fps)
        for noise in parse_list(args.noise)
        for seed in parse_list(args.seeds, int)
    ]
    if args.num_shards > 1:
        jobs = jobs[args.shard :: args.num_shards]
        stem = Path(args.output)
        args.output = str(stem.with_name(f"{stem.stem}.shard{args.shard}-of-{args.num_shards}{stem.suffix}"))
    print(f"Pitches: {len(pitches)} (skipped: {skipped}); jobs: {len(jobs)}; workers: {args.workers}", flush=True)
    rows = []
    with Pool(args.workers, initializer=_init, initargs=(pitches,)) as pool:
        for n, row in enumerate(pool.imap_unordered(_work, jobs, chunksize=8), 1):
            rows.append(row)
            if n % 500 == 0:
                print(f"  {n}/{len(jobs)} done ({time.time() - started:.0f}s)", flush=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = pd.DataFrame(rows).sort_values(["session_pitch", "azimuth_deg", "fps", "noise_body_frac", "seed"])
    result.to_csv(output, index=False)
    meta = {
        "args": vars(args),
        "n_pitches": len(pitches),
        "n_athletes": len({p["user"] for p in pitches}),
        "skipped": skipped,
        "n_rows": len(result),
        "n_errors": int(result["error"].notna().sum()) if "error" in result else 0,
        "detector_version": analyzer.DETECTOR_VERSION,
        "smoothing_window": SMOOTHING_WINDOW,
        "peak_search_ms": PEAK_SEARCH,
        "seconds": round(time.time() - started, 1),
    }
    Path(str(output) + ".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
