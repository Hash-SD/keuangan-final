from __future__ import annotations

from portal_backend.app import create_app


def test_readiness_and_superset_status_endpoints(monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    readiness = client.get("/api/readiness")
    superset = client.get("/api/superset/status")

    assert readiness.status_code == 200
    assert "upload_session" in readiness.get_json()["checks"]
    assert superset.status_code == 200
    assert superset.get_json()["service"]["status"] == "unreachable"
