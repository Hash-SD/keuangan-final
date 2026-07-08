from __future__ import annotations

from portal_backend.app import create_app


def test_runtime_context_persists_readiness_payload(tmp_path, monkeypatch):
    monkeypatch.setattr("portal_backend.app.OUTPUTS_DIR", tmp_path / "outputs")
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.post(
        "/api/runtime-context",
        json={"target_prodi": "Sains Data", "target_tahun_anggaran": "2025"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["readiness"]["context_ready"] is True
    assert (tmp_path / "outputs" / "reports" / "active_runtime_context.json").exists()


def test_uat_submit_writes_auditable_payload(tmp_path, monkeypatch):
    monkeypatch.setattr("portal_backend.app.OUTPUTS_DIR", tmp_path / "outputs")
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.post(
        "/api/uat/submit",
        json={
            "mode": "local_feedback",
            "evaluator": "QA",
            "module": "Portal",
            "scores": [5, 4, 5, 4, 5],
            "feedback": "Draft persistence ok",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["item"]["scores"] == [5, 4, 5, 4, 5]
    assert (tmp_path / "outputs" / "reports" / "uat_local_submissions.json").exists()


def test_readiness_does_not_treat_unreachable_superset_as_ready(monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/readiness")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["checks"]["superset"]["status"] == "unreachable"
    assert payload["status"] == "not_ready"
