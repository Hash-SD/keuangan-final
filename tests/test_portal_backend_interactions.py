from __future__ import annotations

import json

from portal_backend.app import create_app
from portal_backend.services import excel_upload


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


def test_upload_session_status_reports_committed_dataset(tmp_path, monkeypatch):
    raw_file = tmp_path / "data" / "raw" / "excel_lakehouse" / "2025" / "dataset" / "rab.xlsx"
    raw_file.parent.mkdir(parents=True)
    raw_file.write_bytes(b"excel")
    active_path = tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json"
    registry_path = tmp_path / "outputs" / "reports" / "excel_dataset_registry.json"
    active_path.parent.mkdir(parents=True)
    active = {
        "dataset_id": "excel-test",
        "status": "committed",
        "files": [{"filename": "rab.xlsx", "path": str(raw_file)}],
    }
    active_path.write_text(json.dumps(active), encoding="utf-8")
    registry_path.write_text(json.dumps({"active_dataset_id": "excel-test", "datasets": [active]}), encoding="utf-8")
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", registry_path)

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/upload/session/status")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "committed"
    assert payload["active_dataset_id"] == "excel-test"
    assert payload["committed_file_count"] == 1


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
