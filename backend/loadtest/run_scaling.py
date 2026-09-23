#!/usr/bin/env python3
"""Measure throughput and latency with 1, 2, and 4 workers.

Two modes (run inside backend/):

  compose  (default; the official numbers, on Ziyu's Mac)
      python loadtest/run_scaling.py --mode compose
      Uses `docker compose up --scale worker=N` with the fake analyzer set to a fixed
      time, so the test measures the backend, not MediaPipe.

  local    (no Docker; Postgres + Redis already running, env vars set)
      python loadtest/run_scaling.py --mode local
      Starts uvicorn and N `python -m worker.run` processes itself.

Writes loadtest/results/<timestamp>/ with Locust CSVs and summary.md/json.
"""

import argparse
import csv
import json
import os
import platform
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def wait_healthy(url: str, timeout: float = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=3) as response:
                if response.status == 200:
                    return
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit(f"API at {url} not healthy after {timeout}s")


def drain(url: str, timeout: float = 300) -> None:
    """Wait until no job is queued or running, so one run's backlog cannot slow the next."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        busy = 0
        for status in ("queued", "running"):
            try:
                with urllib.request.urlopen(f"{url}/jobs?status={status}&limit=1",
                                            timeout=5) as response:
                    busy += len(json.loads(response.read())["items"])
            except Exception:
                return  # jobs endpoint not available: nothing to wait for
        if busy == 0:
            return
        time.sleep(2)
    print("warning: backlog did not drain before the next run")


def row(stats_csv: Path, name: str) -> dict:
    with stats_csv.open() as handle:
        for record in csv.DictReader(handle):
            if record["Name"] == name:
                return record
    return {}


def summarize(out: Path, workers: int, seconds: float) -> dict:
    stats = out / f"w{workers}_stats.csv"
    job = row(stats, "end_to_end")
    analyze = row(stats, "POST /videos/:id/analyze")
    upload = row(stats, "POST /sessions/:id/videos")
    total = row(stats, "Aggregated")
    finished = int(job.get("Request Count", 0))
    return {
        "workers": workers,
        "jobs_finished": finished,
        "jobs_failed": int(job.get("Failure Count", 0)),
        "jobs_per_min": round(finished / seconds * 60, 1),
        "job_e2e_p50_ms": float(job.get("50%", 0) or 0),
        "job_e2e_p95_ms": float(job.get("95%", 0) or 0),
        "analyze_p50_ms": float(analyze.get("50%", 0) or 0),
        "analyze_p95_ms": float(analyze.get("95%", 0) or 0),
        "upload_p95_ms": float(upload.get("95%", 0) or 0),
        "http_error_rate_pct": round(
            100 * int(total.get("Failure Count", 0)) / max(1, int(total.get("Request Count", 1))),
            2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--mode", choices=["compose", "local"], default="compose")
    parser.add_argument("--workers", default="1,2,4")
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--spawn-rate", type=float, default=5)
    parser.add_argument("--seconds", type=int, default=90)
    parser.add_argument("--analyzer-seconds", type=float, default=3.0,
                        help="Fixed fake-analyzer time per job (use a realistic median).")
    parser.add_argument("--host", default="http://localhost:8000")
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = BACKEND / "loadtest" / "results" / stamp
    out.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "ANALYZER": "fake", "FAKE_ANALYZER_SECONDS": str(args.analyzer_seconds)}
    results = []

    for workers in [int(w) for w in args.workers.split(",")]:
        procs: list[subprocess.Popen] = []
        if args.mode == "compose":
            subprocess.run(["docker", "compose", "up", "-d", "--build", "--scale",
                            f"worker={workers}"], cwd=BACKEND, env=env, check=True)
        else:
            procs.append(subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app.main:app", "--port",
                 args.host.rsplit(":", 1)[-1]], cwd=BACKEND, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
            for _ in range(workers):
                procs.append(subprocess.Popen([sys.executable, "-m", "worker.run"], cwd=BACKEND,
                                              env=env, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL))
        try:
            wait_healthy(args.host)
            subprocess.run(
                [sys.executable, "-m", "locust", "-f", str(BACKEND / "loadtest/locustfile.py"),
                 "--headless", "-u", str(args.users), "-r", str(args.spawn_rate),
                 "-t", f"{args.seconds}s", "--host", args.host, "--csv", str(out / f"w{workers}"),
                 "--only-summary"], cwd=BACKEND, env=env, check=False)
            results.append(summarize(out, workers, args.seconds))
            print(json.dumps(results[-1]))
            drain(args.host)
        finally:
            for proc in procs:
                proc.send_signal(signal.SIGTERM)
            for proc in procs:
                proc.wait(timeout=30)
            if args.mode == "compose":
                subprocess.run(["docker", "compose", "stop", "api", "worker"], cwd=BACKEND,
                               check=False)

    meta = {"mode": args.mode, "users": args.users, "seconds": args.seconds,
            "analyzer_seconds": args.analyzer_seconds, "platform": platform.platform(),
            "cpu_count": os.cpu_count(), "results": results}
    (out / "summary.json").write_text(json.dumps(meta, indent=2))
    header = ("| Workers | Jobs/min | Job end-to-end p50 / p95 (s) | POST analyze p50 / p95 (ms) "
              "| Upload p95 (ms) | Failed jobs | HTTP error % |\n|---|---|---|---|---|---|---|\n")
    lines = [f"| {r['workers']} | {r['jobs_per_min']} | {r['job_e2e_p50_ms'] / 1000:.1f} / "
             f"{r['job_e2e_p95_ms'] / 1000:.1f} | {r['analyze_p50_ms']:.0f} / "
             f"{r['analyze_p95_ms']:.0f} | {r['upload_p95_ms']:.0f} | {r['jobs_failed']} | "
             f"{r['http_error_rate_pct']} |" for r in results]
    note = (f"\n{args.users} users, {args.seconds}s per run, fake analyzer fixed at "
            f"{args.analyzer_seconds}s/job, mode={args.mode}, {platform.platform()}, "
            f"{os.cpu_count()} CPUs.\n")
    (out / "summary.md").write_text(header + "\n".join(lines) + "\n" + note)
    print((out / "summary.md").read_text())


if __name__ == "__main__":
    main()
