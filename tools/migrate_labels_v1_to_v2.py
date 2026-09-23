#!/usr/bin/env python3
"""
Convert a schema v1 label file into schema v2 without changing any frames.

The v1 event frames are stored under one annotation key (default
"A1_anchored", because the existing labels were made by correcting the
algorithm's output rather than blind labeling). Pitcher, hand, view and split
are filled from CLI arguments. The source file is never modified.

Example:
  python tools/migrate_labels_v1_to_v2.py labels/pitch_labels.json \
      labels/pitch_labels_v2.json --pitcher-id P01 --throwing-hand right \
      --split dev --annotation-key A1_anchored
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pitch_labels import EVENT_FIELDS, OPTIONAL_EVENT_FIELDS, default_pitch_uid  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--pitcher-id", required=True)
    parser.add_argument("--throwing-hand", choices=["right", "left"], required=True)
    parser.add_argument("--split", choices=["dev", "test"], required=True)
    parser.add_argument("--view", default=None)
    parser.add_argument("--annotation-key", default="A1_anchored")
    parser.add_argument("--blind", action="store_true", help="Mark the migrated annotation as blind.")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    destination = Path(args.destination)
    if destination.exists() and not args.overwrite:
        raise SystemExit(f"{destination} exists; pass --overwrite to replace it.")

    data = json.loads(Path(args.source).read_text(encoding="utf-8"))
    raw = data if isinstance(data, list) else data.get("pitches", [])
    if isinstance(data, dict) and int(data.get("schema_version", 1)) >= 2:
        raise SystemExit("Source is already schema v2.")

    pitches = []
    for pitch in raw:
        events = {f: pitch[f] for f in EVENT_FIELDS + OPTIONAL_EVENT_FIELDS if pitch.get(f) is not None}
        events["blind"] = bool(args.blind)
        events["label_source"] = pitch.get("label_source")
        migrated = {
            key: value
            for key, value in pitch.items()
            if key not in EVENT_FIELDS + OPTIONAL_EVENT_FIELDS
        }
        migrated.update(
            {
                "pitch_uid": default_pitch_uid(pitch),
                "pitcher_id": args.pitcher_id,
                "throwing_hand": args.throwing_hand,
                "view": args.view,
                "split": args.split,
                "annotations": {args.annotation_key: events},
                "reference": args.annotation_key,
            }
        )
        pitches.append(migrated)

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps({"schema_version": 2, "pitches": pitches}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(pitches)} pitches to {destination}")


if __name__ == "__main__":
    main()
