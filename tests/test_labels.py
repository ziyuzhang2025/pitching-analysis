"""Tests for label loading (schema v1/v2), prefixes, and migration."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pitch_labels import (
    default_pitch_uid,
    load_label_file,
    load_splits,
    safe_token,
)

ROOT = Path(__file__).resolve().parents[1]

V1 = {
    "pitches": [
        {"video_path": "videos/a.MP4", "pitch_id": "window_1", "start_time": 1.0, "end_time": 2.0,
         "front_foot_strike_frame": 40, "pelvis_peak_frame": 44, "trunk_peak_frame": 46, "ball_release_frame": 47},
        {"video_path": "videos/b.MP4", "pitch_id": "window_1", "start_time": 3.0, "end_time": 4.0,
         "front_foot_strike_frame": 100, "pelvis_peak_frame": 104, "trunk_peak_frame": 105, "ball_release_frame": 107},
    ]
}

V2 = {
    "schema_version": 2,
    "pitches": [
        {"pitch_uid": "S01_P03_w01", "video_path": "videos/S01/P03.MOV", "pitcher_id": "P03",
         "throwing_hand": "left", "view": "arm_side", "fps": 240.0, "split": "test",
         "start_time": 1.0, "end_time": 2.5,
         "annotations": {"A1_pass1": {"front_foot_strike_frame": 300, "ball_release_frame": 345},
                          "A2_pass1": {"front_foot_strike_frame": 301, "ball_release_frame": 344}},
         "reference": "A1_pass1"},
        {"pitch_uid": "S01_P04_w01", "video_path": "videos/S01/P04.MOV", "pitcher_id": "P04",
         "throwing_hand": "right", "view": "behind", "fps": 240.0, "split": "dev",
         "start_time": 5.0, "end_time": 6.5,
         "annotations": {"A1_pass1": {"front_foot_strike_frame": 1300, "ball_release_frame": 1346}},
         "reference": "A1_pass1"},
    ],
}


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_v1_loads_with_unique_uids(tmp_path):
    pitches = load_label_file(_write(tmp_path, "v1.json", V1))
    uids = [p["pitch_uid"] for p in pitches]
    assert uids == ["a_window_1", "b_window_1"]
    assert pitches[0]["front_foot_strike_frame"] == 40
    assert pitches[0]["schema_version"] == 1


def test_v1_bare_list(tmp_path):
    pitches = load_label_file(_write(tmp_path, "v1list.json", V1["pitches"]))
    assert len(pitches) == 2


def test_v2_reference_and_override(tmp_path):
    path = _write(tmp_path, "v2.json", V2)
    ref = load_label_file(path)
    assert ref[0]["front_foot_strike_frame"] == 300
    assert ref[0]["throwing_hand"] == "left"
    assert ref[0]["annotation_key"] == "A1_pass1"
    assert ref[0]["pelvis_peak_frame"] is None  # signal events are not human-labeled in v2
    with pytest.raises(KeyError):
        load_label_file(path, annotation_key="A2_pass1")  # second pitch lacks A2


def test_v2_split_filter(tmp_path):
    path = _write(tmp_path, "v2.json", V2)
    assert [p["pitch_uid"] for p in load_label_file(path, split="dev")] == ["S01_P04_w01"]
    assert [p["pitch_uid"] for p in load_label_file(path, split="test")] == ["S01_P03_w01"]


def test_duplicate_uid_rejected(tmp_path):
    dup = {"schema_version": 2, "pitches": [V2["pitches"][0], V2["pitches"][0]]}
    with pytest.raises(ValueError, match="Duplicate"):
        load_label_file(_write(tmp_path, "dup.json", dup))


def test_invalid_split_rejected(tmp_path):
    bad = json.loads(json.dumps(V2))
    bad["pitches"][0]["split"] = "train"
    with pytest.raises(ValueError):
        load_label_file(_write(tmp_path, "bad.json", bad))


def test_safe_token_and_default_uid():
    assert safe_token("a b/c") == "a_b_c"
    assert default_pitch_uid({"video_path": "videos/IMG 1.MOV", "pitch_id": "w 2"}) == "IMG_1_w_2"


def test_evaluator_prefixes_unique_across_videos(tmp_path):
    evaluator = pytest.importorskip("evaluate_pitch_accuracy")
    pitches = load_label_file(_write(tmp_path, "v1.json", V1))
    prefixes = {evaluator.pitch_output_prefix("eval", p) for p in pitches}
    assert len(prefixes) == len(pitches)


def test_real_label_file_has_unique_uids_if_present():
    path = ROOT / "labels" / "pitch_labels.json"
    if not path.exists():
        pytest.skip("local labels not present")
    pitches = load_label_file(path)
    assert len({p["pitch_uid"] for p in pitches}) == len(pitches)


def test_migration_roundtrip(tmp_path):
    src = _write(tmp_path, "v1.json", V1)
    dst = tmp_path / "v2.json"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "migrate_labels_v1_to_v2.py"), str(src), str(dst),
         "--pitcher-id", "P01", "--throwing-hand", "right", "--split", "dev"],
        check=True, capture_output=True,
    )
    before = load_label_file(src)
    after = load_label_file(dst)
    fields = ["pitch_uid", "front_foot_strike_frame", "pelvis_peak_frame", "trunk_peak_frame", "ball_release_frame"]
    assert [[p[f] for f in fields] for p in before] == [[p[f] for f in fields] for p in after]
    assert all(p["annotation_key"] == "A1_anchored" and p["split"] == "dev" for p in after)


def test_splits_file_valid():
    mapping = load_splits(ROOT / "labels" / "splits.json")
    assert all(v in ("dev", "test") for v in mapping.values())
