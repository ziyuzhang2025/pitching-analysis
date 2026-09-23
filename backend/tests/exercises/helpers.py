"""Helpers shared by exercise tests."""

import importlib
from datetime import date

import pytest

from tests.conftest import make_video_bytes


def need(module: str, name: str):
    """Import module.name or fail with a pointer to the exercise."""
    try:
        return getattr(importlib.import_module(module), name)
    except (ImportError, AttributeError):
        pytest.fail(f"{module}.{name} is missing - see docs/backend_exercises.md", pytrace=False)


def api_athlete(client, code="P01", hand="right"):
    response = client.post("/athletes", json={"code": code, "throwing_hand": hand})
    assert response.status_code == 201, response.text
    return response.json()


def api_session(client, athlete_id, day=date(2026, 10, 1)):
    response = client.post(f"/athletes/{athlete_id}/sessions",
                           json={"recorded_on": day.isoformat(), "location": "Bullpen"})
    assert response.status_code == 201, response.text
    return response.json()


def api_upload(client, session_id, content=None, filename="clip.mp4", view="arm_side"):
    content = content if content is not None else make_video_bytes()
    data = {"view": view} if view else {}
    return client.post(f"/sessions/{session_id}/videos",
                       files={"file": (filename, content, "video/mp4")}, data=data)


def api_video(client, content=None, filename="clip.mp4", code="P01"):
    athlete = api_athlete(client, code=code)
    session = api_session(client, athlete["id"])
    response = api_upload(client, session["id"], content=content, filename=filename)
    assert response.status_code == 201, response.text
    return response.json()
