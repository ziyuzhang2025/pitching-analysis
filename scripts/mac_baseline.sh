#!/usr/bin/env bash
# Run on Ziyu's Mac (the official environment, mediapipe 0.10.21) from the repo root:
#   bash scripts/mac_baseline.sh
# It (1) runs the unit tests, (2) re-evaluates the 10 existing dev labels with
# the current detector, and (3) checks the numbers match the June baseline.
# Results must come from the Mac: other MediaPipe builds give different frames.
set -euo pipefail
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
export MPLCONFIGDIR=/private/tmp/mplconfig
mkdir -p "$MPLCONFIGDIR" outputs

"$PY" -m pip install -q -r requirements-dev.txt

echo "== 1/3 unit tests"
"$PY" -m pytest -q tests

echo "== 2/3 labels v2 (created from labels/pitch_labels.json if missing)"
if [ ! -f labels/pitch_labels_v2.json ]; then
  "$PY" tools/migrate_labels_v1_to_v2.py labels/pitch_labels.json labels/pitch_labels_v2.json \
    --pitcher-id P01 --throwing-hand right --split dev --annotation-key A1_anchored
fi

echo "== 3/3 dev-set evaluation with the current detector"
"$PY" evaluate_pitch_accuracy.py --labels labels/pitch_labels_v2.json --split dev \
  --output-prefix baseline_v1 --output-csv outputs/baseline_detector-v1.0.csv | tail -32

"$PY" - <<'PY'
import csv, json, platform
import mediapipe, cv2
rows = list(csv.DictReader(open("outputs/baseline_detector-v1.0.csv")))
expected = {  # outputs/pitch_accuracy_evaluation.csv from June 2026 (same 10 pitches)
    "front_foot_strike": 0.0, "pelvis_peak": 1.5, "trunk_peak": 0.5, "ball_release": 0.1}
result = {}
for event, want in expected.items():
    errors = [abs(int(r[f"{event}_frame_error"])) for r in rows if r[f"{event}_frame_error"] not in ("", None)]
    got = sum(errors) / len(errors) if errors else None
    result[event] = {"mean_abs_frame_error": got, "june_baseline": want,
                     "matches": got is not None and abs(got - want) < 1e-9}
result["environment"] = {"mediapipe": mediapipe.__version__, "opencv": cv2.__version__,
                         "platform": f"{platform.system()} {platform.machine()}"}
json.dump(result, open("outputs/baseline_detector-v1.0.json", "w"), indent=2)
print(json.dumps(result, indent=2))
print("ALL MATCH" if all(v.get("matches") for k, v in result.items() if k != "environment")
      else "MISMATCH - tell Claude before tagging")
PY
echo "Done. Results: outputs/baseline_detector-v1.0.csv and .json"
