"""Analyzer adapters used by the worker.

The analysis core (analyze_pitch_timing.py, auto_detect_pitch_windows.py) stays a
standalone library/CLI. The backend only calls it through this interface, so tests
and load tests can swap in FakeAnalyzer without MediaPipe.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.config import Settings, get_settings

EVENT_NAMES = (
    "front_foot_strike",
    "pelvis_peak",
    "trunk_peak",
    "ball_release",
    "pelvis_peak_velocity",
)


class AnalyzerError(RuntimeError):
    """Raised when analysis fails; the worker decides whether to retry."""


@dataclass(frozen=True)
class EventResult:
    name: str
    frame: int
    time_s: float
    method: str = "auto"
    confidence: float | None = None


@dataclass(frozen=True)
class PitchResult:
    window_index: int
    start_frame: int
    end_frame: int
    events: list[EventResult] = field(default_factory=list)


@dataclass(frozen=True)
class AnalysisOutput:
    fps: float | None
    width: int | None
    height: int | None
    pitches: list[PitchResult]
    environment: dict = field(default_factory=dict)


class Analyzer(Protocol):
    version: str

    def analyze(self, video_path: Path, throwing_hand: str) -> AnalysisOutput: ...


def core_detector_version(repo_dir: Path | None = None) -> str:
    """Read DETECTOR_VERSION from analyze_pitch_timing.py without importing it
    (importing would pull in OpenCV and MediaPipe)."""
    repo_dir = repo_dir or get_settings().analyzer_repo_dir
    try:
        text = (Path(repo_dir) / "analyze_pitch_timing.py").read_text(encoding="utf-8")
    except OSError:
        return "unknown"
    match = re.search(r'^DETECTOR_VERSION\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    return match.group(1) if match else "unknown"


class FakeAnalyzer:
    """Deterministic stand-in: sleeps, then returns two pitches.

    A file whose content starts with FAIL_MARKER always raises AnalyzerError, which
    lets tests and demos exercise retries and failure handling.
    """

    FAIL_MARKER = b"FORCE_FAIL"

    def __init__(self, seconds: float = 0.0, version: str | None = None) -> None:
        self.seconds = seconds
        self.version = version or f"fake-{core_detector_version()}"

    def analyze(self, video_path: Path, throwing_hand: str) -> AnalysisOutput:
        if self.seconds > 0:
            time.sleep(self.seconds)
        path = Path(video_path)
        if path.exists():
            with path.open("rb") as handle:
                if handle.read(len(self.FAIL_MARKER)) == self.FAIL_MARKER:
                    raise AnalyzerError(f"FakeAnalyzer forced failure for {path.name}")
        fps = 240.0
        pitches = []
        for index, base in enumerate((1000, 2200)):
            frames = {
                "front_foot_strike": base,
                "pelvis_peak": base + 8,
                "trunk_peak": base + 12,
                "ball_release": base + 30,
                "pelvis_peak_velocity": base + 9,
            }
            events = [EventResult(n, f, round(f / fps, 4)) for n, f in frames.items()]
            pitches.append(PitchResult(index + 1, base - 240, base + 240, events))
        return AnalysisOutput(
            fps=fps, width=1920, height=1080, pitches=pitches,
            environment={"analyzer": "fake", "throwing_hand": throwing_hand},
        )


REPORT_EVENT_KEYS = {
    "front_foot_strike": "front_foot_strike_frame",
    "pelvis_peak": "pelvis_peak_frame",
    "trunk_peak": "trunk_peak_frame",
    "ball_release": "ball_release_frame",
    "pelvis_peak_velocity": "pelvis_peak_velocity_frame",
}


def parse_timing_report(report: dict, window_index: int, start_frame: int,
                        end_frame: int) -> PitchResult:
    """Convert one analyzer timing_report.json into a PitchResult."""
    fps = float(report.get("fps") or 0) or None
    events = []
    for name, key in REPORT_EVENT_KEYS.items():
        frame = report.get(key)
        if frame is None:
            continue
        method = report.get(f"{name}_detection_method", "auto")
        time_s = round(int(frame) / fps, 4) if fps else 0.0
        events.append(EventResult(name, int(frame), time_s, str(method)))
    return PitchResult(window_index, start_frame, end_frame, events)


class RealAnalyzer:
    """Runs the repository scripts in a temp directory (needs MediaPipe/OpenCV).

    1. auto_detect_pitch_windows.py finds pitch windows in the whole video.
    2. analyze_pitch_timing.py runs on each window with the same search settings
       auto_detect_pitch_windows.py --run-analysis uses.
    """

    ANALYSIS_ARGS = [
        "--peak-search-start-ms", "0", "--pelvis-peak-search-end-ms", "250",
        "--trunk-peak-search-end-ms", "300", "--ball-release-search-start-ms", "30",
        "--ball-release-search-end-ms", "250",
    ]

    def __init__(self, settings: Settings | None = None, max_windows: int = 20,
                 timeout_seconds: int = 1800) -> None:
        self.settings = settings or get_settings()
        self.repo = Path(self.settings.analyzer_repo_dir)
        self.max_windows = max_windows
        self.timeout_seconds = timeout_seconds
        self.version = core_detector_version(self.repo)

    def _run(self, args: list[str], cwd: Path) -> None:
        try:
            subprocess.run([sys.executable, *args], cwd=cwd, check=True, capture_output=True,
                           text=True, timeout=self.timeout_seconds)
        except subprocess.CalledProcessError as exc:
            tail = (exc.stderr or exc.stdout or "")[-2000:]
            raise AnalyzerError(f"{Path(args[0]).name} failed: {tail}") from exc
        except subprocess.TimeoutExpired as exc:
            raise AnalyzerError(f"{Path(args[0]).name} timed out") from exc

    def analyze(self, video_path: Path, throwing_hand: str) -> AnalysisOutput:
        video_path = Path(video_path).resolve()
        with tempfile.TemporaryDirectory(prefix="pitchlab_") as tmp:
            out = Path(tmp)
            self._run([str(self.repo / "auto_detect_pitch_windows.py"), str(video_path),
                       "--throwing-hand", throwing_hand, "--output-prefix", "job",
                       "--max-windows", str(self.max_windows), "--output-dir", str(out)],
                      cwd=self.repo)
            windows_report = json.loads((out / "job_pitch_windows.json").read_text())
            fps = windows_report.get("fps")
            pitches: list[PitchResult] = []
            environment: dict = {}
            for index, window in enumerate(windows_report.get("windows", []), start=1):
                prefix = f"job_w{index}"
                self._run([str(self.repo / "analyze_pitch_timing.py"), str(video_path),
                           "--throwing-hand", throwing_hand,
                           "--start-time", f"{window['start_time']:.3f}",
                           "--end-time", f"{window['end_time']:.3f}",
                           *self.ANALYSIS_ARGS, "--output-dir", str(out),
                           "--output-prefix", prefix], cwd=self.repo)
                report = json.loads((out / f"{prefix}_timing_report.json").read_text())
                environment = report.get("environment", environment)
                start = int(round(window["start_time"] * fps)) if fps else 0
                end = int(round(window["end_time"] * fps)) if fps else 0
                pitches.append(parse_timing_report(report, index, start, end))
        return AnalysisOutput(fps=fps, width=None, height=None, pitches=pitches,
                              environment=environment)


def get_analyzer(settings: Settings | None = None) -> Analyzer:
    settings = settings or get_settings()
    if settings.analyzer == "real":
        return RealAnalyzer(settings)
    return FakeAnalyzer(seconds=settings.fake_analyzer_seconds)
