"""Unit tests for agent-written helpers: pagination, storage, analyzers, queue."""

import io
import json

import pytest

from app.errors import APIError


def test_cursor_round_trip():
    from app.pagination import decode_cursor, encode_cursor

    assert decode_cursor(encode_cursor(42)) == 42
    assert decode_cursor(None) is None
    with pytest.raises(APIError):
        decode_cursor("not-a-cursor")


def test_clamp_limit():
    from app.pagination import MAX_LIMIT, clamp_limit

    assert clamp_limit(10_000) == MAX_LIMIT
    with pytest.raises(APIError):
        clamp_limit(0)


def test_local_storage_streams_and_hashes(tmp_path):
    import hashlib

    from app.storage import LocalStorage

    storage = LocalStorage(tmp_path)
    data = b"x" * (3 * 1024 * 1024 + 5)
    stored = storage.save_stream(io.BytesIO(data), ".MOV", max_bytes=10 * 1024 * 1024)
    assert stored.size == len(data)
    assert stored.sha256 == hashlib.sha256(data).hexdigest()
    assert stored.key.endswith(".mov")
    assert storage.path_for(stored.key).read_bytes() == data
    assert not list(tmp_path.glob(".*.part"))
    storage.delete(stored.key)
    assert not storage.path_for(stored.key).exists()


def test_local_storage_rejects_too_large_and_empty(tmp_path):
    from app.storage import LocalStorage

    storage = LocalStorage(tmp_path)
    with pytest.raises(APIError) as too_big:
        storage.save_stream(io.BytesIO(b"x" * 100), ".mp4", max_bytes=10)
    assert too_big.value.status_code == 413
    with pytest.raises(APIError) as empty:
        storage.save_stream(io.BytesIO(b""), ".mp4", max_bytes=10)
    assert empty.value.status_code == 400
    assert list(tmp_path.iterdir()) == []


def test_storage_blocks_path_traversal(tmp_path):
    from app.storage import LocalStorage

    with pytest.raises(APIError):
        LocalStorage(tmp_path).path_for("../../etc/passwd")


def test_fake_analyzer_output_and_failure(tmp_path):
    from app.analyzers import AnalyzerError, FakeAnalyzer

    output = FakeAnalyzer().analyze(tmp_path / "clip.mp4", "right")
    assert output.fps == 240.0 and len(output.pitches) == 2
    names = {e.name for e in output.pitches[0].events}
    assert {"front_foot_strike", "ball_release"} <= names
    bad = tmp_path / "bad.mp4"
    bad.write_bytes(FakeAnalyzer.FAIL_MARKER + b"rest")
    with pytest.raises(AnalyzerError):
        FakeAnalyzer().analyze(bad, "right")


def test_core_detector_version_reads_repo_file(tmp_path):
    from app.analyzers import core_detector_version

    (tmp_path / "analyze_pitch_timing.py").write_text('X = 1\nDETECTOR_VERSION = "9.8.7"\n')
    assert core_detector_version(tmp_path) == "9.8.7"
    assert core_detector_version(tmp_path / "missing") == "unknown"


def test_parse_timing_report():
    from app.analyzers import parse_timing_report

    report = {"fps": 240.0, "front_foot_strike_frame": 480, "ball_release_frame": 516,
              "pelvis_peak_frame": None, "front_foot_strike_detection_method": "auto"}
    pitch = parse_timing_report(report, 1, 400, 600)
    assert [(e.name, e.frame, e.time_s) for e in pitch.events] == [
        ("front_foot_strike", 480, 2.0), ("ball_release", 516, 2.15)]


def test_real_analyzer_runs_scripts_and_parses(tmp_path, monkeypatch):
    """RealAnalyzer orchestration, with subprocess faked (no MediaPipe needed)."""
    import app.analyzers as analyzers
    from app.config import Settings

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "analyze_pitch_timing.py").write_text('DETECTOR_VERSION = "1.0.0"\n')
    calls = []

    def fake_run(args, cwd, check, capture_output, text, timeout):
        calls.append(args)
        out = __import__("pathlib").Path(args[args.index("--output-dir") + 1])
        if args[1].endswith("auto_detect_pitch_windows.py"):
            (out / "job_pitch_windows.json").write_text(json.dumps(
                {"fps": 60.0, "windows": [{"start_time": 1.0, "end_time": 2.0}]}))
        else:
            prefix = args[args.index("--output-prefix") + 1]
            (out / f"{prefix}_timing_report.json").write_text(json.dumps(
                {"fps": 60.0, "front_foot_strike_frame": 80, "ball_release_frame": 95,
                 "environment": {"mediapipe": "x"}}))

    monkeypatch.setattr(analyzers.subprocess, "run", fake_run)
    analyzer = analyzers.RealAnalyzer(Settings(analyzer="real", analyzer_repo_dir=repo))
    output = analyzer.analyze(tmp_path / "v.mp4", "left")
    assert analyzer.version == "1.0.0"
    assert len(calls) == 2 and "--throwing-hand" in calls[0]
    assert output.pitches[0].start_frame == 60 and output.pitches[0].end_frame == 120
    assert output.environment == {"mediapipe": "x"}


def test_enqueue_immediate_and_delayed(redis_conn, queued_job_ids):
    from app.queue import enqueue_analysis, get_queue

    enqueue_analysis(7)
    enqueue_analysis(8, delay_seconds=30)
    assert get_queue().count == 1
    assert queued_job_ids() == [7, 8]


def test_migration_0001_downgrades_cleanly(clean_db):
    from sqlalchemy import create_engine, inspect

    from tests.conftest import run_migrations

    run_migrations(clean_db, "base", downgrade=True)
    engine = create_engine(clean_db)
    assert "athletes" not in inspect(engine).get_table_names()
    engine.dispose()
    run_migrations(clean_db, "head")
