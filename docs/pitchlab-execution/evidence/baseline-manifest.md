# Baseline manifest

Status: PARTIAL / RESEARCH BLOCKED. Inspection date: 2026-10-14. This is sufficient as the backend preflight, not as a reproducible detector baseline.

## Checkout and environment

- Revision: `dc449a1807787a023e9590fa643351f3b2a528dd`.
- Pre-existing untracked paths at inspection: `.lavish/`, `docs/pitchlab-execution/`, `docs/superpowers/`. `graphify-out/` was created during this audit.
- Python: 3.12.13; platform: macOS 26.3.1 arm64.
- Root environment: MediaPipe 0.10.21, OpenCV 4.11.0.86, NumPy 1.26.4, Pandas 3.0.3. Pytest was absent.
- Detector version declared by `analyze_pitch_timing.py`: `1.0.0`.
- Root verification: 20 passed in 9.23 seconds using pytest installed into an isolated temporary directory.
- Docker daemon: unavailable. Backend integration and exercise tests were not executed.

## Selected historical artifact set

Prefix: `outputs/ui_test_pitch_01_20260622_121032`. The set contains window candidates, detected windows and five windows of plots, debug data, landmarks, overlays and timing reports. Recorded report metadata says 30 fps and 2,401 original frames; this metadata is not independently verified against the absent source.

Representative SHA-256 values:

- pitch windows: `ca214081cfe1c5fc4f52bd3634bba91223bbe3f6ce05e6a16ca748e9a7dfa0df`
- window 1 report: `a8b7e8cfae939071c946128b9d8a2f7d111670febdcdfdac376e7a734542d0d4`
- window 1 landmarks: `c9e4de622965007313c1343e23355f2330055744bef19762bb45c01f5c2a7eb0`
- window 1 overlay: `659bd73123484f4d65001fe466e47ea54b32bf0ac54fc25450b70e4c353d1a4e`

The full checksum command and output are recorded in the verification log. No files were regenerated.

## Missing provenance

- original source-video path and checksum;
- exact generation command and effective CLI/UI configuration;
- confirmation that current detector version produced these files;
- reproducibility tolerance from a fresh rerun.

Because these fields are absent, task 01.01 remains BLOCKED for research reproducibility. They do not block deterministic fake-analyzer backend exercises. Do not infer accuracy from these artifacts.
