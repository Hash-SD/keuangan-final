from __future__ import annotations

from portal_backend.app import create_app


def test_production_readiness_is_fail_closed_without_release_gate(tmp_path, monkeypatch):
    from portal_backend import app as app_module

    monkeypatch.setattr(app_module, "OUTPUTS_DIR", tmp_path / "outputs")
    response = create_app().test_client().get("/api/production/readiness")

    payload = response.get_json()
    assert response.status_code == 503
    assert payload["status"] == "NOT_READY_FOR_USER_UPLOAD"
    assert payload["blocking_errors"]
