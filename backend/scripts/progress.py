#!/usr/bin/env python3
"""Show exercise progress: python scripts/progress.py   (run inside backend/)

Needs Postgres and Redis running (e.g. `docker compose up -d postgres redis`).
Exit code 0 only when every exercise passes (CI treats it as informational).
"""

import re
import subprocess
import sys
from pathlib import Path

EXERCISES = [
    ("1", "Models + migration 0002", "test_ex1_models.py"),
    ("2", "Job state machine + retry policy", "test_ex2_state_machine.py"),
    ("3", "Sessions + video upload API", "test_ex3_sessions_videos_api.py"),
    ("4", "Idempotency + races", "test_ex4_idempotency.py"),
    ("5", "Worker task + job API", "test_ex5_worker_and_jobs.py"),
    ("6", "Crash recovery (reaper)", "test_ex6_reaper.py"),
    ("7", "Versioned results + backfill", "test_ex7_results_and_backfill.py"),
]


def count(output: str, word: str) -> int:
    match = re.search(rf"(\d+) {word}", output)
    return int(match.group(1)) if match else 0


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    all_done = True
    print(f"{'Ex':<3} {'Topic':<34} {'Passed':>8}")
    for number, topic, filename in EXERCISES:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider",
             f"tests/exercises/{filename}"],
            cwd=root, capture_output=True, text=True,
        )
        tail = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        passed = count(tail, "passed")
        total = passed + count(tail, "failed") + count(tail, "error")
        mark = "done" if total and passed == total else "todo"
        all_done &= mark == "done"
        print(f"{number:<3} {topic:<34} {passed:>3}/{total:<3} {mark}")
    return 0 if all_done else 1


if __name__ == "__main__":
    sys.exit(main())
