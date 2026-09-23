"""Exercise 3: sessions and video upload endpoints."""

import hashlib

from tests.conftest import make_video_bytes
from tests.exercises.helpers import api_athlete, api_session, api_upload


def test_create_and_list_sessions(client):
    athlete = api_athlete(client)
    first = api_session(client, athlete["id"])
    assert first["athlete_id"] == athlete["id"] and first["location"] == "Bullpen"
    for _ in range(4):
        api_session(client, athlete["id"])
    page = client.get(f"/athletes/{athlete['id']}/sessions", params={"limit": 3}).json()
    assert [s["id"] for s in page["items"]] == [1, 2, 3] and page["next_cursor"]
    rest = client.get(f"/athletes/{athlete['id']}/sessions",
                      params={"limit": 3, "cursor": page["next_cursor"]}).json()
    assert [s["id"] for s in rest["items"]] == [4, 5] and rest["next_cursor"] is None


def test_sessions_are_scoped_to_athlete(client):
    a = api_athlete(client, "A")
    b = api_athlete(client, "B")
    api_session(client, a["id"])
    assert client.get(f"/athletes/{b['id']}/sessions").json()["items"] == []


def test_session_for_missing_athlete_is_404(client):
    response = client.post("/athletes/99/sessions", json={"recorded_on": "2026-10-01"})
    assert response.status_code == 404
    assert client.get("/athletes/99/sessions").status_code == 404


def test_session_validation(client):
    athlete = api_athlete(client)
    api_session(client, athlete["id"])
    bad = client.post(f"/athletes/{athlete['id']}/sessions", json={"recorded_on": "yesterday"})
    assert bad.status_code == 422


def test_upload_video(client):
    session = api_session(client, api_athlete(client)["id"])
    content = make_video_bytes("v", 5000)
    response = api_upload(client, session["id"], content=content, filename="Pitch 1.MOV")
    assert response.status_code == 201, response.text
    video = response.json()
    assert video["sha256"] == hashlib.sha256(content).hexdigest()
    assert video["bytes"] == 5000 and video["filename"] == "Pitch 1.MOV"
    assert video["view"] == "arm_side" and video["fps"] is None
    assert client.get(f"/videos/{video['id']}").json() == video


def test_upload_without_view(client):
    session = api_session(client, api_athlete(client)["id"])
    assert api_upload(client, session["id"], view=None).json()["view"] is None


def test_upload_stores_file(client):
    from app.config import get_settings

    session = api_session(client, api_athlete(client)["id"])
    api_upload(client, session["id"])
    stored = [p for p in get_settings().storage_dir.iterdir() if not p.name.startswith(".")]
    assert len(stored) == 1


def test_upload_rejects_bad_extension_and_missing_session(client):
    session = api_session(client, api_athlete(client)["id"])
    bad = api_upload(client, session["id"], filename="notes.txt")
    assert bad.status_code == 415
    assert bad.json()["error"]["code"] == "unsupported_media_type"
    assert api_upload(client, 999).status_code == 404


def test_upload_rejects_invalid_view(client):
    session = api_session(client, api_athlete(client)["id"])
    assert api_upload(client, session["id"], view="sideways").status_code == 422


def test_upload_too_large(client, monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "100")
    from app.config import get_settings

    get_settings.cache_clear()
    session = api_session(client, api_athlete(client)["id"])
    response = api_upload(client, session["id"], content=b"x" * 1000)
    assert response.status_code == 413


def test_missing_video_is_404(client):
    assert client.get("/videos/12345").status_code == 404
