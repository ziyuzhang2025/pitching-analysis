# RQ2 findings: what a single camera can recover (OBP simulation)

Generated 2026-09-23 from `research/results/rq2_summary.json`,
`rq2_tables.csv`, and `rq2_noise_tables.csv`. Regenerate with
`scripts/download_obp.sh`, `research/obp_simulation.py` (sharded), and
`research/obp_summary.py`. Every number below is copied from those files.

**Setup.** 402 pitches from 100 athletes (OpenBiomechanics Project; 9 of 411
pitches lack foot-contact or release events). 3D joint centers (360 Hz) were
projected into a horizontal orthographic camera, resampled to 30/60/120/240 fps
with random phase, and run through the unchanged analyzer event functions
(detector 1.0.0, 5-frame smoothing). Ground truth: `fp_10_time` (foot contact),
`BR_time`, and the argmax of `pelvis_velo_z` / `torso_velo_z` between them.
Errors are median absolute errors with 95% bootstrap CIs that resample athletes.
"True FFS" rows replace the automatic foot strike with the lab value, to isolate
the rotation proxy. "Ideal pseudo-3D" is the rotation of the hip or shoulder
line in the ground plane, computed from the true 3D joint centers. It is an
upper bound for a world-landmark method, not a MediaPipe result.

## 1. The pelvis→trunk gap is mostly below phone resolution

Lab pelvis→trunk peak delay: median 8.3 ms (IQR 0.0–13.9). 91.5% of pitches are
under one 30 fps frame (33.3 ms), and in 20.6% the trunk peaks first.

## 2. Side view (90°), by frame rate

| fps | FFS | BR | Pelvis, current rule† | Pelvis, 2D true peak† | Pelvis, ideal pseudo-3D | Trunk, 2D† |
|---|---|---|---|---|---|---|
| 30 | 17.7 [15.3, 20.3] | 25.6 [23.1, 27.7] | 56.4 [52.6, 59.8] | 23.1 [18.2, 29.0] | 28.0 [25.5, 30.9] | 50.5 [43.7, 55.9] |
| 60 | 16.8 [15.0, 19.8] | 14.9 [13.3, 16.0] | 32.0 [27.2, 36.1] | 27.3 [21.5, 32.6] | 12.4 [11.0, 14.0] | 28.0 [24.6, 31.5] |
| 120 | 15.0 [12.6, 18.4] | 15.5 [14.8, 16.1] | 18.0 [15.0, 20.6] | 26.3 [22.4, 32.5] | 4.0 [3.5, 4.4] | 23.8 [21.4, 28.3] |
| 240 | 16.1 [13.0, 18.7] | 15.5 [14.8, 16.1] | 13.4 [11.7, 18.4] | 26.9 [22.8, 32.7] | **2.7 [2.2, 3.3]** | 23.8 [19.8, 27.4] |

All values are ms. † = with the true foot strike.

- **A 2D true-peak pelvis proxy does not improve with frame rate** (≈ 23–27 ms). The error is in the proxy, not the sampling.
- **The ideal pseudo-3D pelvis angle reaches 2.7 ms at 240 fps.** This motivates world landmarks (RQ3).
- **The current "onset" rule lands close to the true 3D peak at 240 fps** (13.4 ms, median signed −2.6 ms). That looks coincidental: at 30 fps it is 56 ms early.
- **FFS and BR have systematic late biases** at 90°: median signed +15.4 ms (FFS) and +14.4 ms (BR) at 240 fps. Only 34% (FFS) and 11% (BR) fall within ±10 ms. Both are correctable with a dev-set bias estimate. Note that FFS ground truth is 10% bodyweight on a force plate, which is not identical to visible contact.
- **The shoulder joint-center line is a poor trunk proxy even in 3D** (28 ms at 240 fps).

## 3. Camera position matters more than frame rate (240 fps)

| Azimuth | FFS | BR | Pelvis, 2D true peak† | Pelvis, current rule† | Trunk, 2D† |
|---|---|---|---|---|---|
| 0 (behind) | 243.9 | 19.2 | 72.4 | 60.0 | 22.7 |
| 30 | 175.5 | 21.0 | 50.3 | 58.2 | 9.4 |
| 60 | 15.3 | 21.5 | **15.0** | 33.6 | 11.7 |
| 90 (side) | 16.1 | 15.5 | 26.9 | **13.4** | 23.8 |
| 120 | 16.4 | 125.2 | 166.7 | 46.8 | 162.0 |
| 150 | 21.6 | 158.6 | 153.7 | 55.4 | 188.4 |
| 180 (front) | 243.2 | 19.4 | 73.0 | 59.2 | 22.0 |

- The FFS rule fails for views along the pitching direction (0°, 180°), because the stride moves toward or away from the camera.
- BR and the rotation peaks fail at 120–150° (front-oblique).
- 60–90° (side to rear-oblique) is the only region where all events work. **A second phone at about 60° is a better choice than directly behind.**
- With an orthographic camera, θ and θ+180° are mirror images and give identical results. Occlusion (glove side vs arm side) is **not** modeled.

## 4. The sequence (pelvis before trunk) is not recoverable

At 90° and 240 fps, the order was correct in 63.7% of pitches (current rule), 48.8% (2D true peak, i.e. chance), and 64.7% (ideal pseudo-3D).

The current rule reports "pelvis first" in 92.8% of pitches; the lab data says 68.9%. Its apparent accuracy comes from that bias: for pitches where the trunk actually peaks first, it is right only about 2% of the time (see `paper/figs/rq2_order_by_gap.png`). **Do not report kinematic-sequence classifications from single-camera video.**

## 5. Landmark noise hurts the FFS rule at high frame rates

Noise as the SD of Gaussian landmark jitter in body-height units. The white-noise frame-to-frame jitter in the existing Mac landmark files was estimated at about 0.1%: a median of 0.0009, IQR 0.0004–0.0022, from 175 CSVs. This is a rough estimate that ignores MediaPipe's temporal smoothing and systematic errors.

| 90°, 240 fps | noise 0 | 0.1% | 0.3% | 1% |
|---|---|---|---|---|
| FFS | 16.1 | 29.1 | 58.0 | 85.3 |
| BR | 15.5 | 19.1 | 19.5 | 24.2 |
| Pelvis, current rule† | 13.4 | 14.4 | 16.0 | 20.8 |

At 60 fps the FFS error with 1% noise is 32.9 ms, and at 60° / 240 fps it reaches 105.9 ms with 0.3% noise. **Cause:** the smoothing window (5 frames) and the ankle stability/speed thresholds are defined per frame. At 240 fps, 5 frames is only 21 ms, and differentiated noise scales with fps. **Fix for detector 1.1 (dev set only):** define smoothing and stability windows in milliseconds, not frames.

## Limitations

- Orthographic camera without perspective, lens distortion, occlusion, or motion blur.
- Lab joint centers are not MediaPipe landmarks: MediaPipe's systematic errors (such as hip placement during rotation) are not modeled, only white jitter.
- The population is mostly college-level (OBP `playing_level`).
- The FFS truth is force-based, not visual.
- Single smoothing setting (5 frames).
