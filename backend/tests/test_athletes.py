"""Tests for the worked example resource. Use them as a template for the exercises."""

import pytest


def create(client, code="P01", hand="right", height=1.80):
    return client.post("/athletes", json={"code": code, "throwing_hand": hand, "height_m": height})


def test_create_and_get(client):
    response = create(client)
    assert response.status_code == 201
    athlete = response.json()
    assert athlete["code"] == "P01" and athlete["throwing_hand"] == "right"
    fetched = client.get(f"/athletes/{athlete['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == athlete


def test_duplicate_code_is_409(client):
    assert create(client).status_code == 201
    response = create(client)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_missing_is_404(client):
    response = client.get("/athletes/999")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Athlete 999 not found"


@pytest.mark.parametrize("height", [0.5, 3.0])
def test_height_is_validated(client, height):
    assert create(client, height=height).status_code == 422


def test_cursor_pagination_walks_all_rows(client):
    for i in range(7):
        assert create(client, code=f"P{i:02d}").status_code == 201
    seen, cursor, pages = [], None, 0
    while True:
        params = {"limit": 3} | ({"cursor": cursor} if cursor else {})
        body = client.get("/athletes", params=params).json()
        seen += [a["code"] for a in body["items"]]
        pages += 1
        cursor = body["next_cursor"]
        if cursor is None:
            break
    assert seen == [f"P{i:02d}" for i in range(7)]
    assert pages == 3


def test_bad_cursor_and_limit(client):
    assert client.get("/athletes", params={"cursor": "!!!"}).json()["error"]["code"] == "bad_cursor"
    assert client.get("/athletes", params={"limit": 0}).status_code == 400


def test_database_rejects_invalid_hand_even_without_api(db):
    from sqlalchemy.exc import IntegrityError

    from app.models import Athlete

    db.add(Athlete(code="X", throwing_hand="both"))
    with pytest.raises(IntegrityError):
        db.commit()
