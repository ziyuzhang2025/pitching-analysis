"""Exercise 7: versioned results and the backfill endpoint."""

from tests.conftest import make_video_bytes
from tests.exercises.helpers import api_video, need


def analyzed_video(client, tag="a", code="P01"):
    video = api_video(client, content=make_video_bytes(tag), code=code)
    job = client.post(f"/videos/{video['id']}/analyze").json()
    need("worker.tasks", "run_analysis_job")(job["id"])
    return video, job


def test_results_shape_and_order(client):
    video, job = analyzed_video(client)
    body = client.get(f"/videos/{video['id']}/results").json()
    assert body["job_id"] == job["id"] and body["detector_version"] == job["detector_version"]
    assert [p["window_index"] for p in body["pitches"]] == [1, 2]
    frames = [e["frame"] for e in body["pitches"][0]["events"]]
    assert frames == sorted(frames) and len(frames) == 5


def test_results_errors(client):
    assert client.get("/videos/999/results").json()["error"]["code"] == "not_found"
    video = api_video(client)
    client.post(f"/videos/{video['id']}/analyze")
    response = client.get(f"/videos/{video['id']}/results")
    assert response.status_code == 404 and response.json()["error"]["code"] == "no_results"


def test_results_by_version(client, db):
    AnalysisJob = need("app.models", "AnalysisJob")
    video, job = analyzed_video(client)
    row = db.get(AnalysisJob, job["id"])
    row.detector_version = "0.9.0"
    db.commit()
    assert client.get(f"/videos/{video['id']}/results",
                      params={"detector_version": "0.9.0"}).status_code == 200
    assert client.get(f"/videos/{video['id']}/results",
                      params={"detector_version": "2.0.0"}).status_code == 404


def test_reanalyze_backfills_only_missing(client, queued_job_ids):
    done_video, _ = analyzed_video(client, "a", "P01")
    pending = api_video(client, content=make_video_bytes("b"), code="P02")
    active = client.post(f"/videos/{pending['id']}/analyze").json()
    fresh = api_video(client, content=make_video_bytes("c"), code="P03")
    before = queued_job_ids()

    response = client.post("/admin/reanalyze")
    assert response.status_code == 202
    body = response.json()
    assert body["enqueued"] == 1 and len(body["job_ids"]) == 1
    new_job = client.get(f"/jobs/{body['job_ids'][0]}").json()
    assert new_job["video_id"] == fresh["id"]
    assert sorted(queued_job_ids()) == sorted(before + body["job_ids"])
    assert active["id"] not in body["job_ids"]
    assert done_video["id"] != new_job["video_id"]

    second = client.post("/admin/reanalyze").json()
    assert second["enqueued"] == 0 and second["job_ids"] == []


def test_reanalyze_new_version_covers_all(client):
    analyzed_video(client, "a", "P01")
    analyzed_video(client, "b", "P02")
    body = client.post("/admin/reanalyze", params={"detector_version": "9.9.9"}).json()
    assert body["detector_version"] == "9.9.9" and body["enqueued"] == 2
