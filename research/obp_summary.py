#!/usr/bin/env python3
"""
Summarize the OBP single-camera simulation (research/obp_simulation.py).

Merges shard CSVs, computes median absolute timing errors with 95% bootstrap
confidence intervals that resample ATHLETES (clustered bootstrap, not pitches),
and writes:
  research/results/rq2_summary.json   key numbers for the paper/README
  research/results/rq2_tables.csv     long table of every condition
  paper/figs/rq2_*.pdf|png            figures

Orthographic projection makes azimuth theta and theta+180 mirror images, so
figures show 0-180 degrees. Data: OpenBiomechanics Project (CC BY-NC-SA 4.0).
"""

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

ERROR_COLUMNS = {
    "ffs_err_ms": "Front foot strike (auto)",
    "br_err_ms": "Ball release (auto)",
    "pelvis_onset_err_ms": "Pelvis, current rule (onset, auto FFS)",
    "pelvis_peakvel_err_ms": "Pelvis, 2D true peak (auto FFS)",
    "oracle_pelvis_onset_err_ms": "Pelvis, current rule (true FFS)",
    "oracle_pelvis_peakvel_err_ms": "Pelvis, 2D true peak (true FFS)",
    "top_pelvis_err_ms": "Pelvis, ideal pseudo-3D",
    "trunk_err_ms": "Trunk, 2D peak (auto FFS)",
    "oracle_trunk_err_ms": "Trunk, 2D peak (true FFS)",
    "top_trunk_err_ms": "Trunk, ideal pseudo-3D (shoulder line)",
    "oracle_br_err_ms": "Ball release (true FFS)",
}
ORDER_COLUMNS = ["order_ok_current_rule", "order_ok_peakvel", "order_ok_oracle_peakvel", "order_ok_top"]
# One fixed color + marker per method/entity across every figure (validated with
# the dataviz palette validator, light mode; markers are the secondary encoding).
STYLE = {
    "current": ("#2a78d6", "o"),   # 2D image-plane proxy, current (onset) rule
    "peak2d": ("#eb6834", "s"),    # 2D image-plane proxy, true peak
    "top": ("#1baf7a", "^"),       # idealized pseudo-3D (ground-plane angle)
    "ffs": ("#eda100", "D"),       # front foot strike
    "br": ("#e87ba4", "v"),        # ball release
}
TEXT = "#0b0b0b"
MUTED = "#52514e"


def load(pattern):
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No simulation CSVs match {pattern}")
    frame = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    if "error" in frame:
        failed = frame["error"].notna().sum()
        frame = frame[frame["error"].isna()].drop(columns=["error"])
    else:
        failed = 0
    return frame, files, int(failed)


def clustered_median_ci(values, clusters, n_boot=1000, seed=2026):
    """Median of |values| with a 95% CI from resampling clusters (athletes)."""
    data = pd.DataFrame({"v": np.abs(values), "c": clusters}).dropna()
    if data.empty:
        return np.nan, np.nan, np.nan, 0
    groups = [g["v"].to_numpy() for _, g in data.groupby("c")]
    rng = np.random.default_rng(seed)
    stats = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        stats.append(np.median(np.concatenate([groups[i] for i in pick])))
    return (float(np.median(data["v"])), float(np.percentile(stats, 2.5)),
            float(np.percentile(stats, 97.5)), int(len(data)))


def condition_table(frame, n_boot):
    rows = []
    base = frame[frame["noise_body_frac"] == 0] if "noise_body_frac" in frame else frame
    for (az, fps, noise), group in frame.groupby(["azimuth_deg", "fps", "noise_body_frac"]):
        for column, label in ERROR_COLUMNS.items():
            if column not in group:
                continue
            med, lo, hi, n = clustered_median_ci(group[column].to_numpy(), group["user"].to_numpy(), n_boot)
            signed = group[column].dropna()
            rows.append({
                "azimuth_deg": az, "fps": fps, "noise_body_frac": noise, "metric": column, "label": label,
                "median_abs_ms": med, "ci_low": lo, "ci_high": hi,
                "median_signed_ms": float(signed.median()) if len(signed) else np.nan,
                "p90_abs_ms": float(signed.abs().quantile(0.9)) if len(signed) else np.nan,
                "within_10ms_pct": float((signed.abs() <= 10).mean() * 100) if len(signed) else np.nan,
                "detected_pct": float(group[column].notna().mean() * 100),
                "n": n,
            })
        for column in ORDER_COLUMNS:
            if column in group:
                rows.append({"azimuth_deg": az, "fps": fps, "noise_body_frac": noise, "metric": column,
                             "label": column, "order_accuracy_pct": float(group[column].mean() * 100),
                             "n": int(group[column].notna().sum())})
    del base
    return pd.DataFrame(rows)


def pick(table, metric, az, fps, noise=0.0):
    row = table[(table.metric == metric) & (table.azimuth_deg == az) & (table.fps == fps) & (table.noise_body_frac == noise)]
    if row.empty:
        return None
    r = row.iloc[0]
    if "order" in metric:
        return {"order_accuracy_pct": round(r["order_accuracy_pct"], 1), "n": int(r["n"])}
    return {"median_abs_ms": round(r["median_abs_ms"], 1),
            "ci95": [round(r["ci_low"], 1), round(r["ci_high"], 1)],
            "median_signed_ms": round(r["median_signed_ms"], 1),
            "within_10ms_pct": round(r["within_10ms_pct"], 1), "n": int(r["n"])}


def style_axes(ax, title, xlabel, ylabel):
    ax.set_title(title, loc="left", fontsize=10, color=TEXT)
    ax.set_xlabel(xlabel, fontsize=9, color=MUTED)
    ax.set_ylabel(ylabel, fontsize=9, color=MUTED)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c9c8c2")


def line_series(ax, xs, ys, lows, highs, key, label):
    color, marker = STYLE[key]
    ax.fill_between(xs, lows, highs, color=color, alpha=0.12, linewidth=0)
    ax.plot(xs, ys, color=color, linewidth=2, marker=marker, markersize=5, label=label)


def figures(frame, table, fig_dir, fps_main, az_side):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir.mkdir(parents=True, exist_ok=True)
    t0 = table[table.noise_body_frac == 0]
    written = []

    # 1. Pelvis error vs camera azimuth (true FFS isolates the proxy)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    series = [("oracle_pelvis_onset_err_ms", "2D, current rule (onset)", "current"),
              ("oracle_pelvis_peakvel_err_ms", "2D, true peak", "peak2d"),
              ("top_pelvis_err_ms", "Ideal pseudo-3D (ground plane)", "top")]
    for metric, label, i in series:
        rows = t0[(t0.metric == metric) & (t0.fps == fps_main) & (t0.azimuth_deg <= 180)].sort_values("azimuth_deg")
        line_series(ax, rows.azimuth_deg, rows.median_abs_ms, rows.ci_low, rows.ci_high, i, label)
    ax.set_xticks(range(0, 181, 30))
    ax.set_xticklabels(["0\nbehind", "30", "60", "90\narm side", "120", "150", "180\nfront"])
    style_axes(ax, f"Pelvis peak timing error by camera position ({int(fps_main)} fps)",
               "Camera azimuth (degrees)", "Median |error| (ms)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"rq2_pelvis_error_by_azimuth.{ext}", dpi=200)
    plt.close(fig)
    written.append("rq2_pelvis_error_by_azimuth")

    # 2. Error vs frame rate at the side view
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.3), sharey=False)
    panels = [
        ("Pelvis peak", [("oracle_pelvis_onset_err_ms", "2D, current rule (onset)", "current"),
                         ("oracle_pelvis_peakvel_err_ms", "2D, true peak", "peak2d"),
                         ("top_pelvis_err_ms", "Ideal pseudo-3D", "top")]),
        ("Observable events", [("ffs_err_ms", "Front foot strike", "ffs"),
                               ("br_err_ms", "Ball release", "br")]),
    ]
    for ax, (title, metrics) in zip(axes, panels):
        for metric, label, i in metrics:
            rows = t0[(t0.metric == metric) & (t0.azimuth_deg == az_side)].sort_values("fps")
            line_series(ax, rows.fps, rows.median_abs_ms, rows.ci_low, rows.ci_high, i, label)
        ax.set_xscale("log", base=2)
        ax.set_xticks([30, 60, 120, 240])
        ax.set_xticklabels(["30", "60", "120", "240"])
        style_axes(ax, f"{title} ({int(az_side)} deg view)", "Frame rate (fps)", "Median |error| (ms)")
        ax.legend(frameon=False, fontsize=7.5)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"rq2_error_by_fps.{ext}", dpi=200)
    plt.close(fig)
    written.append("rq2_error_by_fps")

    # 3. Sequence order accuracy vs true pelvis->trunk gap
    subset = frame[(frame.noise_body_frac == 0) & (frame.fps == fps_main) & (frame.azimuth_deg == az_side)].copy()
    bins = [-np.inf, 0, 10, 20, 40, np.inf]
    names = ["<=0", "0-10", "10-20", "20-40", ">40"]
    subset["gap_bin"] = pd.cut(subset.true_gap_ms, bins=bins, labels=names)
    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    width = 0.26
    order_series = [("order_ok_current_rule", "2D, current rule (onset)", "current"),
                    ("order_ok_oracle_peakvel", "2D, true peak", "peak2d"),
                    ("order_ok_top", "Ideal pseudo-3D", "top")]
    x = np.arange(len(names))
    for i, (column, label, key) in enumerate(order_series):
        values = subset.groupby("gap_bin", observed=False)[column].mean().reindex(names) * 100
        ax.bar(x + (i - 1) * width, values, width=width - 0.03, color=STYLE[key][0], label=label)
    counts = subset.groupby("gap_bin", observed=False).size().reindex(names)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{n}\n(n={c})" for n, c in zip(names, counts)])
    ax.axhline(50, color=MUTED, linewidth=1, linestyle="--")
    ax.text(-0.45, 51, "chance", fontsize=7.5, color=MUTED, ha="left", va="bottom")
    ax.set_ylim(0, 118)
    ax.set_yticks(range(0, 101, 20))
    style_axes(ax, f"Pelvis-before-trunk order recovered ({int(fps_main)} fps, {int(az_side)} deg view)",
               "True pelvis-to-trunk peak gap (ms)", "Correct order (%)")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=3)
    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"rq2_order_by_gap.{ext}", dpi=200)
    plt.close(fig)
    written.append("rq2_order_by_gap")
    return written


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--inputs", default="outputs/rq2/rq2_main*.csv")
    parser.add_argument("--results-dir", default="research/results")
    parser.add_argument("--fig-dir", default="paper/figs")
    parser.add_argument("--fps-main", type=float, default=240.0)
    parser.add_argument("--side-azimuth", type=float, default=90.0)
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--prefix", default="rq2")
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args()

    frame, files, failed = load(args.inputs)
    table = condition_table(frame, args.bootstrap)
    results = Path(args.results_dir)
    results.mkdir(parents=True, exist_ok=True)
    table.to_csv(results / f"{args.prefix}_tables.csv", index=False)

    az, fmain = args.side_azimuth, args.fps_main
    gap = frame.drop_duplicates("session_pitch")["true_gap_ms"]
    summary = {
        "source": "OpenBiomechanics Project (CC BY-NC-SA 4.0); research/obp_simulation.py",
        "inputs": files,
        "n_rows": int(len(frame)),
        "failed_rows": failed,
        "n_pitches": int(frame.session_pitch.nunique()),
        "n_athletes": int(frame.user.nunique()),
        "conditions": {
            "azimuth_deg": sorted(frame.azimuth_deg.unique().tolist()),
            "fps": sorted(frame.fps.unique().tolist()),
            "noise_body_frac": sorted(frame.noise_body_frac.unique().tolist()),
        },
        "ci_method": f"95% percentile bootstrap resampling athletes, {args.bootstrap} resamples",
        "true_pelvis_to_trunk_gap_ms": {
            "median": round(float(gap.median()), 1),
            "q25": round(float(gap.quantile(0.25)), 1),
            "q75": round(float(gap.quantile(0.75)), 1),
            "share_below_one_frame_30fps_pct": round(float((gap < 1000 / 30).mean() * 100), 1),
            "share_negative_pct": round(float((gap < 0).mean() * 100), 1),
        },
        "side_view_by_fps": {
            str(int(f)): {m: pick(table, m, az, f) for m in list(ERROR_COLUMNS) + ORDER_COLUMNS}
            for f in sorted(frame.fps.unique())
        },
        f"by_azimuth_at_{int(fmain)}fps": {
            str(int(a)): {m: pick(table, m, a, fmain) for m in
                          ["ffs_err_ms", "br_err_ms", "oracle_pelvis_onset_err_ms",
                           "oracle_pelvis_peakvel_err_ms", "top_pelvis_err_ms", "oracle_trunk_err_ms"]}
            for a in sorted(frame.azimuth_deg.unique())
        },
    }
    if not args.no_figures:
        summary["figures"] = figures(frame, table, Path(args.fig_dir), fmain, az)
    out = results / f"{args.prefix}_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {out} and {results / (args.prefix + '_tables.csv')}")


if __name__ == "__main__":
    main()
