"""Exercise 4: idempotent uploads and job submission, including real races."""

import threading
from concurrent.futures import ThreadPoolExecutor

from tests.conftest import make_video_bytes
from tests.exercises.helpers import api_athlete, api_session, api_upload, api_video, need


def test_duplicate_upload_returns_existing_video(client):
    from app.config import get_settings

    session = api_session(client, api_athlete(client)["id"])
    content = make_video_bytes("d")
    first = api_upload(client, session["id"], content=content)
    second = api_upload(client, session["id"], content=content, filename="renamed.mp4")
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    files = [p for p in get_settings().storage_dir.iterdir() if not p.name.startswith(".")]
    assert len(files) == 1, "the duplicate upload's file must be deleted"


def test_same_file_in_another_session_is_a_new_video(client):
    athlete = api_athlete(client)
    s1, s2 = api_session(client, athlete["id"]), api_session(client, athlete["id"])
    content = make_video_bytes("s")
    assert api_upload(client, s1["id"], content=content).status_code == 201
    assert api_upload(client, s2["id"], content=content).status_code == 201


def test_analyze_creates_and_enqueues_once(client, queued_job_ids):
    video = api_video(client)
    first = client.post(f"/videos/{video['id']}/analyze")
    assert first.status_code == 202, first.text
    job = first.json()
    assert job["status"] == "queued" and job["attempts"] == 0 and job["max_attempts"] == 3
    assert job["detector_version"].startswith("fake-")
    again = client.post(f"/videos/{video['id']}/analyze")
    assert again.status_code == 200 and again.json()["id"] == job["id"]
    assert queued_job_ids() == [job["id"]], "an existing job must not be enqueued twice"


def test_idempotency_key(client, queued_job_ids):
    video = api_video(client)
    headers = {"Idempotency-Key": "abc-1"}
    first = client.post(f"/videos/{video['id']}/analyze", headers=headers).json()
    second = client.post(f"/videos/{video['id']}/analyze", headers=headers)
    assert second.status_code == 200 and second.json()["id"] == first["id"]
    other = api_video(client, content=make_video_bytes("o"), code="P02")
    conflict = client.post(f"/videos/{other['id']}/analyze", headers=headers)
    assert conflict.status_code == 409
    assert queued_job_ids() == [first["id"]]


def test_analyze_missing_video_is_404(client):
    assert client.post("/videos/999/analyze").status_code == 404


def _setup_video(db):
    from datetime import date

    from app.models import Athlete
    from app.storage import StoredFile

    TrainingSession = need("app.models", "TrainingSession")
    athlete = Athlete(code="R1", throwing_hand="right")
    db.add(athlete)
    db.flush()
    session = TrainingSession(athlete_id=athlete.id, recorded_on=date(2026, 10, 1))
    db.add(session)
    db.commit()
    return session.id, StoredFile


def _race(n, fn):
    barrier = threading.Barrier(n)

    def run(i):
        barrier.wait()
        return fn(i)

    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(run, range(n)))


def test_concurrent_video_creation_race(db):
    """8 threads insert the same file at the same moment: exactly one creates it."""
    from app.db import session_factory

    find_or_create_video = need("app.services.idempotency", "find_or_create_video")
    session_id, StoredFile = _setup_video(db)

    def attempt(i):
        with session_factory()() as s:
            stored = StoredFile(key=f"k{i}.mp4", sha256="b" * 64, size=10)
            video, created = find_or_create_video(s, session_id, stored, "clip.mp4", None)
            return video.id, created

    results = _race(8, attempt)
    assert sum(created for _, created in results) == 1
    assert len({vid for vid, _ in results}) == 1


def test_concurrent_job_submission_race(db):
    """8 threads submit the same video at once: one job, everyone gets its id."""
    from app.db import session_factory
    from app.storage import StoredFile

    find_or_create_video = need("app.services.idempotency", "find_or_create_video")
    get_or_create_job = need("app.services.idempotency", "get_or_create_job")
    session_id, _ = _setup_video(db)
    video, _ = find_or_create_video(db, session_id, StoredFile("k.mp4", "c" * 64, 10),
                                    "clip.mp4", None)
    video_id = video.id

    def attempt(i):
        with session_factory()() as s:
            job, created = get_or_create_job(s, video_id, "1.0.0", None, 3)
            return job.id, created

    results = _race(8, attempt)
    assert sum(created for _, created in results) == 1
    assert len({jid for jid, _ in results}) == 1
