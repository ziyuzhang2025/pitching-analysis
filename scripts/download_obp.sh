#!/usr/bin/env bash
# Download the OpenBiomechanics Project (OBP) pitching files used by the
# lab-data simulation (docs/RESEARCH_GUIDE.md, Phase 4).
#
# License: CC BY-NC-SA 4.0 with an extra clause: anyone employed by or
# associated with a professional sports organization or financial analysis
# firm may not use the data. Non-commercial use only; cite OBP.
# https://github.com/drivelineresearch/openbiomechanics
set -euo pipefail

DEST="${1:-data/external/obp}"
REL="https://github.com/drivelineresearch/openbiomechanics/releases/download/dataset-v1"
RAW="https://raw.githubusercontent.com/drivelineresearch/openbiomechanics/main/baseball_pitching/data"
mkdir -p "$DEST"

fetch() { # url output
  if [ -s "$2" ]; then echo "exists: $2"; return; fi
  echo "downloading: $1"
  curl -fsSL --retry 3 -o "$2.part" "$1" && mv "$2.part" "$2"
}

fetch "$REL/pitching_landmarks.zip"   "$DEST/pitching_landmarks.zip"
fetch "$REL/pitching_joint_velos.zip" "$DEST/pitching_joint_velos.zip"
fetch "$RAW/poi/poi_metrics.csv"      "$DEST/poi_metrics.csv"
fetch "$RAW/metadata.csv"             "$DEST/metadata.csv"

for zip in pitching_landmarks.zip pitching_joint_velos.zip; do
  unzip -o -q "$DEST/$zip" -d "$DEST"
done

# Record checksums so later runs can confirm the same data was used.
( cd "$DEST" && sha256sum landmarks.csv joint_velos.csv poi_metrics.csv metadata.csv > SHA256SUMS.txt 2>/dev/null \
  || shasum -a 256 landmarks.csv joint_velos.csv poi_metrics.csv metadata.csv > SHA256SUMS.txt )
cat "$DEST/SHA256SUMS.txt"
echo "OBP files ready in $DEST"
