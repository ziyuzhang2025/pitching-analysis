"""Exercise 5: the worker task and job endpoints."""

from datetime import datetime, timezone

import pytest

from tests.conftest import make_video_bytes
from tests.exercises.helpers import api_video, need

FAILING_CONTENT = b"FORCE_FAIL" + make_video_bytes("f")  # FakeAnalyzer always fails on this


def run_job(job_id):
    need("worker.tasks", "run_analysis_job")(job_id)


def submit(client, filename="clip.mp4", content=None, code="P01"):
    video = api_video(client, filename=filename, content=content, code=code)
    job = client.post(f"/videos/{video['id']}/analyze").json()
    return video, job


def test_successful_job(client, db):
    Pitch = need("app.models", "Pitch")
    video, job = submit(client)
    run_job(job["id"])
    done = client.get(f"/jobs/{job['id']}").json()
    assert done["status"] == "succeeded" and done["attempts"] == 1
    assert done["started_at"] and done["finished_at"] and done["error"] is None
    assert db.query(Pitch).filter_by(job_id=job["id"]).count() == 2
    assert client.get(f"/videos/{video['id']}").json()["fps"] == 240.0


def test_worker_ignores_non_queued_jobs(client, db):
    Pitch = need("app.models", "Pitch")
    _, job = submit(client)
    run_job(job["id"])
    run_job(job["id"])  # duplicate queue message
    assert db.query(Pitch).filter_by(job_id=job["id"]).count() == 2
    assert client.get(f"/jobs/{job['id']}").json()["attempts"] == 1
    run_job(987654)  # unknown id: no exception


def test_failure_is_retried_with_backoff(client, queued_job_ids):
    _, job = submit(client, content=FAILING_CONTENT)
    queued_job_ids_before = queued_job_ids()
    run_job(job["id"])
    after = client.get(f"/jobs/{job['id']}").json()
    assert after["status"] == "queued" and after["attempts"] == 1
    assert "forced failure" in after["error"]
    assert queued_job_ids().count(job["id"]) == queued_job_ids_before.count(job["id"]) + 1


def test_failure_after_max_attempts(client):
    _, job = submit(client, content=FAILING_CONTENT)
    for _ in range(3):
        run_job(job["id"])
    final = client.get(f"/jobs/{job['id']}").json()
    assert final["status"] == "failed" and final["attempts"] == 3 and final["finished_at"]


def test_retry_replaces_partial_results(client, db):
    """Rows left by an earlier attempt must not be duplicated."""
    Pitch = need("app.models", "Pitch")
    _, job = submit(client)
    db.add(Pitch(job_id=job["id"], window_index=1, start_frame=0, end_frame=1))
    db.commit()
    run_job(job["id"])
    assert db.query(Pitch).filter_by(job_id=job["id"]).count() == 2


def test_analysis_runs_outside_transaction(client, monkeypatch):
    """While the analyzer runs, the job row must already say 'running' to others."""
    import app.analyzers as analyzers

    _, job = submit(client)
    seen = {}
    real_analyze = analyzers.FakeAnalyzer.analyze

    def spy(self, path, hand):
        from app.db import session_factory

        with session_factory()() as other:
            AnalysisJob = need("app.models", "AnalysisJob")
            seen["status"] = other.get(AnalysisJob, job["id"]).status
        return real_analyze(self, path, hand)

    monkeypatch.setattr(analyzers.FakeAnalyzer, "analyze", spy)
    run_job(job["id"])
    assert seen["status"] == "running", "commit the claim before analyzing"


def test_job_endpoints(client):
    _, j1 = submit(client)
    _, j2 = submit(client, content=make_video_bytes("z"), code="P02")
    run_job(j1["id"])
    assert client.get("/jobs/999").status_code == 404
    everything = client.get("/jobs").json()
    assert [j["id"] for j in everything["items"]] == [j1["id"], j2["id"]]
    succeeded = client.get("/jobs", params={"status": "succeeded"}).json()["items"]
    assert [j["id"] for j in succeeded] == [j1["id"]]
    page = client.get("/jobs", params={"limit": 1}).json()
    assert len(page["items"]) == 1 and page["next_cursor"]
    assert client.get("/jobs", params={"status": "paused"}).status_code == 422


@pytest.mark.parametrize("attempts_before", [0])
def test_timestamps_are_timezone_aware(client, attempts_before):
    _, job = submit(client)
    run_job(job["id"])
    body = client.get(f"/jobs/{job['id']}").json()
    started = datetime.fromisoformat(body["started_at"])
    assert started.tzinfo is not None and started <= datetime.now(timezone.utc)
