#!/usr/bin/env python3
"""
Load pitch event labels in schema v1 or v2 and normalize them.

Schema v1 (legacy): {"pitches": [{video_path, pitch_id, start_time, end_time,
<event>_frame, ...}]} or a bare list of such dicts. Event frames sit directly on
each pitch.

Schema v2: {"schema_version": 2, "pitches": [{pitch_uid, video_path,
pitcher_id, throwing_hand, view, fps, split, start_time, end_time,
annotations: {<annotator>_<pass>: {<event>_frame: int, ...}}, reference:
<annotation key>}]}. See docs/RESEARCH_GUIDE.md, Phase 0.2.

Every normalized pitch is a flat dict carrying the legacy keys the evaluator
already understands (event frames at the top level), plus metadata keys:
pitch_uid, pitcher_id, throwing_hand, view, split, annotation_key,
schema_version. Nothing here depends on MediaPipe or OpenCV.
"""

import json
from pathlib import Path

EVENT_FIELDS = [
    "front_foot_strike_frame",
    "pelvis_peak_frame",
    "trunk_peak_frame",
    "ball_release_frame",
]

OPTIONAL_EVENT_FIELDS = ["max_knee_height_frame"]

METADATA_FIELDS = [
    "pitch_uid",
    "pitcher_id",
    "throwing_hand",
    "view",
    "split",
    "annotation_key",
    "schema_version",
]

VALID_SPLITS = {"dev", "test", None}
VALID_HANDS = {"right", "left", None}


def safe_token(text, default="pitch"):
    """Return a filename-safe token (alphanumerics, dash, underscore)."""
    text = str(text if text is not None else "").strip() or default
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in text)


def default_pitch_uid(pitch):
    """Build a stable unique id from the video file stem and pitch_id."""
    stem = Path(str(pitch.get("video_path", "video"))).stem
    return f"{safe_token(stem, 'video')}_{safe_token(pitch.get('pitch_id'))}"


def _raw_pitches(data):
    if isinstance(data, list):
        return data, 1
    version = int(data.get("schema_version", 1))
    return data.get("pitches", []), version


def normalize_pitch(pitch, schema_version, annotation_key=None):
    """Return a flat pitch dict with top-level event frames and metadata."""
    normalized = {
        key: value for key, value in pitch.items() if key != "annotations"
    }
    chosen_key = None

    if schema_version >= 2:
        annotations = pitch.get("annotations") or {}
        chosen_key = annotation_key or pitch.get("reference")
        if chosen_key is None and len(annotations) == 1:
            chosen_key = next(iter(annotations))
        if chosen_key is not None and chosen_key not in annotations:
            raise KeyError(
                f"Annotation '{chosen_key}' not found for pitch "
                f"{pitch.get('pitch_uid') or pitch.get('pitch_id')}; "
                f"available: {sorted(annotations)}"
            )
        chosen = annotations.get(chosen_key, {}) if chosen_key else {}
        for field in EVENT_FIELDS + OPTIONAL_EVENT_FIELDS:
            normalized[field] = chosen.get(field)
        if "pitch_id" not in normalized:
            normalized["pitch_id"] = pitch.get("pitch_uid")

    normalized.setdefault("pitch_uid", None)
    if not normalized["pitch_uid"]:
        normalized["pitch_uid"] = default_pitch_uid(normalized)
    for field in ("pitcher_id", "throwing_hand", "view", "split"):
        normalized.setdefault(field, None)
    normalized["annotation_key"] = chosen_key
    normalized["schema_version"] = schema_version

    if normalized["split"] not in VALID_SPLITS:
        raise ValueError(f"Invalid split {normalized['split']!r} for {normalized['pitch_uid']}")
    if normalized["throwing_hand"] not in VALID_HANDS:
        raise ValueError(
            f"Invalid throwing_hand {normalized['throwing_hand']!r} for {normalized['pitch_uid']}"
        )
    return normalized


def load_label_file(labels_path, annotation_key=None, split=None):
    """Load and normalize labels. Optionally keep only one split."""
    with Path(labels_path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    raw, version = _raw_pitches(data)
    if not raw:
        raise ValueError(f"No labeled pitches found in {labels_path}")

    pitches = [normalize_pitch(p, version, annotation_key) for p in raw]

    uids = [p["pitch_uid"] for p in pitches]
    duplicates = sorted({uid for uid in uids if uids.count(uid) > 1})
    if duplicates:
        raise ValueError(f"Duplicate pitch_uid values in {labels_path}: {duplicates}")

    if split is not None:
        pitches = [p for p in pitches if p.get("split") == split]
        if not pitches:
            raise ValueError(f"No pitches with split={split!r} in {labels_path}")
    return pitches


def load_splits(splits_path):
    """Load labels/splits.json mapping pitcher_id -> 'dev' | 'test'."""
    path = Path(splits_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    mapping = data.get("pitchers", data)
    for pitcher, split in mapping.items():
        if split not in ("dev", "test"):
            raise ValueError(f"Invalid split {split!r} for pitcher {pitcher}")
    return mapping
