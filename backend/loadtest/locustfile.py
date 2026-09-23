"""Load test: upload a small clip, request analysis, poll until the job finishes.

Besides normal request stats, each finished job is recorded as a custom request
"JOB end_to_end" whose response time = submit -> succeeded/failed (queue wait +
processing). Run through loadtest/run_scaling.py, which fixes the analyzer time.
"""

import os
import time
import uuid

from locust import HttpUser, between, events, task

POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "0.5"))
JOB_TIMEOUT_SECONDS = float(os.environ.get("JOB_TIMEOUT_SECONDS", "300"))
CLIP_BYTES = int(os.environ.get("CLIP_BYTES", str(256 * 1024)))


class Coach(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self) -> None:
        code = f"L{uuid.uuid4().hex[:10]}"
        athlete = self.client.post("/athletes", json={"code": code, "throwing_hand": "right"},
                                   name="POST /athletes").json()
        self.session_id = self.client.post(
            f"/athletes/{athlete['id']}/sessions", json={"recorded_on": "2026-10-01"},
            name="POST /athletes/:id/sessions").json()["id"]

    @task
    def upload_analyze_and_wait(self) -> None:
        content = os.urandom(CLIP_BYTES)  # unique bytes -> a new video every time
        video = self.client.post(f"/sessions/{self.session_id}/videos",
                                 files={"file": ("clip.mp4", content, "video/mp4")},
                                 name="POST /sessions/:id/videos").json()
        submitted = time.perf_counter()
        job = self.client.post(f"/videos/{video['id']}/analyze",
                               name="POST /videos/:id/analyze").json()
        status = job["status"]
        while status in ("queued", "running"):
            if time.perf_counter() - submitted > JOB_TIMEOUT_SECONDS:
                break
            time.sleep(POLL_SECONDS)
            status = self.client.get(f"/jobs/{job['id']}", name="GET /jobs/:id").json()["status"]
        elapsed_ms = (time.perf_counter() - submitted) * 1000
        events.request.fire(
            request_type="JOB", name="end_to_end", response_time=elapsed_ms, response_length=0,
            exception=None if status == "succeeded" else RuntimeError(f"job ended {status}"),
            context={},
        )
