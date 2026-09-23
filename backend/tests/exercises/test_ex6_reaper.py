"""Exercise 6: crash recovery for jobs stuck in 'running'."""

from datetime import datetime, timedelta, timezone

from tests.exercises.helpers import api_video, need

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)


def running_job(client, db, started_minutes_ago, attempts=1, code="P01", tag="a"):
    from tests.conftest import make_video_bytes

    AnalysisJob = need("app.models", "AnalysisJob")
    video = api_video(client, content=make_video_bytes(tag), code=code)
    job = client.post(f"/videos/{video['id']}/analyze").json()
    row = db.get(AnalysisJob, job["id"])
    row.status = "running"
    row.attempts = attempts
    row.started_at = NOW - timedelta(minutes=started_minutes_ago)
    db.commit()
    return row.id


def test_stale_job_is_requeued(client, db):
    requeue = need("app.jobs.reaper", "requeue_stale_jobs")
    stale = running_job(client, db, started_minutes_ago=30)
    fresh = running_job(client, db, started_minutes_ago=1, code="P02", tag="b")
    assert requeue(db, NOW, timeout_seconds=900) == [stale]
    db.expire_all()
    AnalysisJob = need("app.models", "AnalysisJob")
    assert db.get(AnalysisJob, stale).status == "queued"
    assert "Timed out" in db.get(AnalysisJob, stale).error
    assert db.get(AnalysisJob, fresh).status == "running"


def test_stale_job_on_last_attempt_fails(client, db):
    requeue = need("app.jobs.reaper", "requeue_stale_jobs")
    stale = running_job(client, db, started_minutes_ago=30, attempts=3)
    assert requeue(db, NOW, timeout_seconds=900) == []
    db.expire_all()
    job = db.get(need("app.models", "AnalysisJob"), stale)
    assert job.status == "failed" and job.finished_at == NOW


def test_requeued_job_can_then_succeed(client, db):
    requeue = need("app.jobs.reaper", "requeue_stale_jobs")
    run = need("worker.tasks", "run_analysis_job")
    stale = running_job(client, db, started_minutes_ago=30)
    requeue(db, NOW, timeout_seconds=900)
    run(stale)
    body = client.get(f"/jobs/{stale}").json()
    assert body["status"] == "succeeded" and body["attempts"] == 2
