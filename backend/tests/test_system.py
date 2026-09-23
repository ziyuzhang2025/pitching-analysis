"""Health, version, request ids, and the shared error shape."""


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": True, "redis": True}


def test_health_degraded_when_redis_down(client, monkeypatch):
    import app.api.health as health

    class Broken:
        def ping(self):
            raise ConnectionError("down")

    monkeypatch.setattr(health, "get_redis", lambda: Broken())
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["redis"] is False


def test_version_reports_fake_analyzer(client):
    body = client.get("/version").json()
    assert body["analyzer"] == "fake"
    assert body["detector_version"].startswith("fake-")


def test_request_id_is_generated_and_echoed(client):
    generated = client.get("/health").headers["X-Request-ID"]
    assert len(generated) == 32
    echoed = client.get("/health", headers={"X-Request-ID": "abc123"}).headers["X-Request-ID"]
    assert echoed == "abc123"


def test_unknown_route_uses_error_shape(client):
    response = client.get("/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_validation_error_shape(client):
    response = client.post("/athletes", json={"code": "bad code!", "throwing_hand": "up"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    fields = {tuple(d["loc"])[-1] for d in error["details"]}
    assert {"code", "throwing_hand"} <= fields


def test_openapi_lists_all_resources(client):
    paths = client.get("/openapi.json").json()["paths"]
    for path in ["/athletes", "/athletes/{athlete_id}/sessions", "/sessions/{session_id}/videos",
                 "/videos/{video_id}/analyze", "/jobs/{job_id}", "/videos/{video_id}/results",
                 "/admin/reanalyze", "/health"]:
        assert path in paths
