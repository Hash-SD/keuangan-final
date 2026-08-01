from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from portal_backend.services.airflow import DAG_ID, get_active_dag_run, get_dag_run, trigger_dag


def test_trigger_dag_sends_dataset_and_pipeline_identity():
    response = Mock(status_code=201, json=lambda: {"dag_run_id": "portal__run-1", "state": "queued"})
    with patch("portal_backend.services.airflow.requests.post", return_value=response) as post:
        result = trigger_dag(dataset_session_id="dataset-1", pipeline_run_id="run-1")

    post.assert_called_once()
    assert post.call_args.kwargs["json"] == {
        "dag_run_id": "portal__run-1",
        "conf": {"dataset_session_id": "dataset-1", "pipeline_run_id": "run-1"},
    }
    assert result["dag_id"] == DAG_ID
    assert result["state"] == "queued"


def test_trigger_dag_reports_airflow_rejection():
    response = Mock(status_code=409, text="DAG is paused")
    with patch("portal_backend.services.airflow.requests.post", return_value=response):
        with pytest.raises(RuntimeError, match="DAG is paused"):
            trigger_dag(dataset_session_id="dataset-1", pipeline_run_id="run-1")


def test_get_dag_run_marks_terminal_state():
    response = Mock(ok=True, status_code=200, json=lambda: {"dag_run_id": "portal__run-1", "state": "failed", "conf": {}})
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        result = get_dag_run("portal__run-1")
    assert result["state"] == "failed"
    assert result["terminal"] is True


def test_failed_airflow_run_quarantines_active_dataset(monkeypatch, tmp_path):
    from portal_backend.app import create_app
    from portal_backend.services import excel_upload

    active_path = tmp_path / "outputs/reports/active.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(
        '{"dataset_id":"dataset-1","dataset_session_id":"dataset-1","status":"committed",'
        '"upload_state":"COMMITTED","files":[{"filename":"rab.xlsx","path":"data/raw/rab.xlsx"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr("portal_backend.app.get_dag_run", lambda _run_id: {
        "dag_id": DAG_ID,
        "dag_run_id": "portal__run-1",
        "state": "failed",
        "conf": {"dataset_session_id": "dataset-1", "pipeline_run_id": "run-1"},
        "terminal": True,
    })

    response = create_app().test_client().get("/api/airflow/runs/portal__run-1")

    assert response.status_code == 200
    assert response.get_json()["dataset_status"] == "failed"
    assert response.get_json()["status"] == "failed"


def test_upload_session_status_ignores_gitkeep_staging_marker(monkeypatch, tmp_path):
    from portal_backend.app import create_app
    from portal_backend.services import excel_upload

    active_path = tmp_path / "outputs/reports/active.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text('{"status":"failed","files":[]}', encoding="utf-8")
    staging = tmp_path / "data/uploads/staging"
    staging.mkdir(parents=True)
    (staging / ".gitkeep").write_text("keep", encoding="utf-8")
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr(excel_upload, "EXCEL_DATASET_REGISTRY_PATH", tmp_path / "outputs/reports/registry.json")
    monkeypatch.setattr(excel_upload, "DATA_DIR", tmp_path / "data")

    response = create_app().test_client().get("/api/upload/session/status")

    assert response.status_code == 200
    assert response.get_json()["staging_file_count"] == 0
    assert response.get_json()["staging_status"] == "empty"


def test_get_active_dag_run_matches_dataset_identity():
    response = Mock(ok=True, status_code=200, text="", json=lambda: {"dag_runs": [
        {"dag_run_id": "portal__run-1", "state": "running", "logical_date": "now", "conf": {"dataset_session_id": "dataset-1"}},
    ]})
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        result = get_active_dag_run("dataset-1")
    assert result["dag_run_id"] == "portal__run-1"
    assert result["state"] == "running"


def test_portal_trigger_endpoint_queues_active_dataset(monkeypatch, tmp_path):
    from portal_backend.app import create_app
    from portal_backend.services import excel_upload

    active_path = tmp_path / "outputs/reports/active.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(
        '{"dataset_id":"dataset-1","dataset_session_id":"dataset-1","status":"committed",'
        '"upload_state":"COMMITTED","files":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr("portal_backend.app.validate_committed_dataset", lambda *_args: {"valid": True, "errors": []})

    monkeypatch.setattr("portal_backend.app.trigger_dag", lambda **kwargs: {
        "dag_id": DAG_ID,
        "dag_run_id": "portal__run-1",
        "dataset_session_id": kwargs["dataset_session_id"],
        "pipeline_run_id": kwargs["pipeline_run_id"],
        "state": "queued",
    })
    response = create_app().test_client().post("/api/airflow/trigger", json={})
    assert response.status_code in {200, 202}
    assert response.get_json()["status"] in {"success", "queued"}
    body = response.get_json()
    assert body.get("dataset_session_id") or body.get("conf", {}).get("dataset_session_id") or body.get("run", {}).get("conf", {}).get("dataset_session_id")


def test_portal_trigger_rejects_partial_active_dataset(monkeypatch, tmp_path):
    from portal_backend.app import create_app
    from portal_backend.services import excel_upload

    active_path = tmp_path / "outputs/reports/active.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(
        '{"dataset_id":"dataset-1","dataset_session_id":"dataset-1","status":"committed",'
        '"upload_state":"COMMITTED","validation_status":"PARTIAL","files":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr("portal_backend.app.trigger_dag", lambda **_: pytest.fail("partial dataset must not trigger Airflow"))

    response = create_app().test_client().post("/api/airflow/trigger", json={})

    assert response.status_code == 400


def test_pipeline_endpoint_returns_error_status_for_failed_local_run(monkeypatch):
    from portal_backend.app import create_app

    monkeypatch.setattr("portal_backend.app.run_full", lambda _mode: {"status": "failed", "steps": []})
    response = create_app().test_client().post("/api/pipeline/full-run-basic", json={})
    assert response.status_code == 500
