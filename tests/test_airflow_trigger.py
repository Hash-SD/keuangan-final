from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from portal_backend.services.airflow import (
    DAG_ID,
    get_active_dag_run,
    get_dag_run,
    get_runtime_snapshot,
    trigger_dag,
)


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


def test_trigger_dag_sends_dashboard_target_conf():
    response = Mock(status_code=201, json=lambda: {"dag_run_id": "portal__run-1", "state": "queued"})
    with patch("portal_backend.services.airflow.requests.post", return_value=response) as post:
        trigger_dag(
            dataset_session_id="dataset-1",
            pipeline_run_id="run-1",
            dashboard_mode="update",
            dashboard_database_id="3",
            dashboard_dashboard_id="2",
        )
    post.assert_called_once()
    assert post.call_args.kwargs["json"]["conf"] == {
        "dataset_session_id": "dataset-1",
        "pipeline_run_id": "run-1",
        "dashboard_mode": "update",
        "dashboard_database_id": "3",
        "dashboard_dashboard_id": "2",
    }


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


def test_dag_run_progress_groups_tasks_into_stages():
    from portal_backend.services.airflow import _dag_run_progress

    payload = {
        "task_instances": [
            {"task_id": "validate_upload_context", "state": "success", "start_date": "2026-01-01T00:00:00Z", "end_date": "2026-01-01T00:01:00Z"},
            {"task_id": "extract_excel_to_bronze", "state": "success", "start_date": "2026-01-01T00:01:00Z", "end_date": "2026-01-01T00:02:00Z"},
            {"task_id": "merge_multi_file", "state": "success", "start_date": "2026-01-01T00:02:00Z", "end_date": "2026-01-01T00:03:00Z"},
            {"task_id": "normalize_silver", "state": "running", "start_date": "2026-01-01T00:03:00Z"},
            {"task_id": "refresh_superset_dashboard", "state": "queued"},
            {"task_id": "start", "state": "success"},
        ]
    }
    response = Mock(ok=True, status_code=200, json=lambda: payload)
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        progress = _dag_run_progress("portal__run-1")

    assert progress["stages"]["raw"]["done"] == 3
    assert progress["stages"]["bronze"]["done"] == 1
    assert progress["stages"]["silver"]["running"] == 1
    assert progress["stages"]["bi"]["total"] == 1
    assert "other" not in progress["stages"]


def test_dag_run_progress_uses_airflow_duration_or_airflow_timestamps():
    from portal_backend.services.airflow import _dag_run_progress

    payload = {
        "task_instances": [
            {"task_id": "start", "state": "success", "duration": 0.1},
            {"task_id": "validate_upload_context", "state": "success", "duration": 0.2},
            {
                "task_id": "extract_excel_to_bronze",
                "state": "success",
                "start_date": "2026-01-01T00:00:00Z",
                "end_date": "2026-01-01T00:00:01Z",
            },
            {"task_id": "detect_year_and_format", "state": "success", "duration": 0.4},
            {
                "task_id": "parse_flexible",
                "state": "success",
                "duration": 0.0,
                "start_date": "2026-01-01T00:00:02Z",
                "end_date": "2026-01-01T00:00:02.1Z",
            },
            {"task_id": "merge_multi_file", "state": "running", "start_date": "2026-01-01T00:00:03Z"},
        ]
    }
    response = Mock(ok=True, status_code=200, json=lambda: payload)
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        progress = _dag_run_progress("portal__run-1")

    assert progress["stages"]["raw"]["duration_seconds"] == 1.3
    assert progress["stages"]["bronze"]["duration_seconds"] == 0.5
    assert progress["stages"]["bronze"]["running"] == 1


def test_dag_run_progress_uses_stage_airflow_timestamp_span_for_zero_duration_tasks():
    from portal_backend.services.airflow import _dag_run_progress

    payload = {
        "task_instances": [
            {"task_id": "detect_year_and_format", "state": "success", "duration": 0.0,
             "start_date": "2026-01-01T00:00:00Z", "end_date": "2026-01-01T00:00:00.000001Z"},
            {"task_id": "parse_flexible", "state": "success", "duration": 0.0,
             "start_date": "2026-01-01T00:00:00.2Z", "end_date": "2026-01-01T00:00:00.200001Z"},
            {"task_id": "merge_multi_file", "state": "success", "duration": 0.0,
             "start_date": "2026-01-01T00:00:00.4Z", "end_date": "2026-01-01T00:00:00.400001Z"},
        ]
    }
    response = Mock(ok=True, status_code=200, json=lambda: payload)
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        progress = _dag_run_progress("portal__run-1")

    assert progress["stages"]["bronze"]["duration_seconds"] == 0.4


def test_dag_run_progress_counts_failed_tasks_per_stage():
    from portal_backend.services.airflow import _dag_run_progress

    response = Mock(
        ok=True,
        status_code=200,
        json=lambda: {
            "task_instances": [
                {"task_id": "normalize_silver", "state": "failed"},
                {"task_id": "map_iku_and_nomenklatur", "state": "upstream_failed"},
            ]
        },
    )
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        progress = _dag_run_progress("portal__failed")

    assert progress["stages"]["silver"]["failed"] == 2


def test_get_active_dag_run_matches_dataset_identity():
    response = Mock(ok=True, status_code=200, text="", json=lambda: {"dag_runs": [
        {"dag_run_id": "portal__run-1", "state": "running", "logical_date": "now", "conf": {"dataset_session_id": "dataset-1"}},
    ]})
    with patch("portal_backend.services.airflow.requests.get", return_value=response):
        result = get_active_dag_run("dataset-1")
    assert result["dag_run_id"] == "portal__run-1"
    assert result["state"] == "running"


def test_runtime_snapshot_uses_one_list_request_and_prioritizes_active_run():
    list_response = Mock(
        ok=True,
        status_code=200,
        text="",
        json=lambda: {
            "dag_runs": [
                {
                    "dag_run_id": "portal__active",
                    "state": "running",
                    "conf": {"dataset_session_id": "dataset-1"},
                },
                {
                    "dag_run_id": "portal__latest",
                    "state": "success",
                    "conf": {"dataset_session_id": "dataset-1"},
                },
            ]
        },
    )
    tasks_response = Mock(
        ok=True,
        status_code=200,
        json=lambda: {
            "task_instances": [
                {
                    "task_id": "start",
                    "state": "success",
                    "duration": 0.3,
                }
            ]
        },
    )
    with patch(
        "portal_backend.services.airflow.requests.get",
        side_effect=[list_response, tasks_response],
    ) as get:
        snapshot = get_runtime_snapshot("dataset-1")

    assert get.call_count == 2
    assert snapshot["source"] == "active"
    assert snapshot["active"] is True
    assert snapshot["runtime_run"]["dag_run_id"] == "portal__active"
    assert snapshot["runtime_run"]["progress"]["stages"]["raw"]["duration_seconds"] == 0.3


def test_runtime_endpoint_disables_http_caching(monkeypatch):
    from portal_backend.app import create_app

    monkeypatch.setattr(
        "portal_backend.app.get_runtime_snapshot",
        lambda: {
            "status": "ready",
            "active": True,
            "active_run": {"dag_run_id": "portal__active", "state": "running"},
            "latest_run": None,
            "runtime_run": {"dag_run_id": "portal__active", "state": "running"},
            "source": "active",
        },
    )

    response = create_app().test_client().get("/api/airflow/runtime")

    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store, no-cache, must-revalidate"
    assert response.headers["Pragma"] == "no-cache"


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


def test_portal_trigger_repairs_filename_kinds_before_validation(monkeypatch, tmp_path):
    import portal_backend.app as app_module
    from portal_backend.app import create_app
    from portal_backend.services import excel_upload

    raw_dir = tmp_path / "data/raw/excel_lakehouse/dataset-1"
    raw_dir.mkdir(parents=True)
    rab = raw_dir / "RAB_2025_SD_RAB_IKU.xlsx"
    nomenklatur = raw_dir / "Nomenklatur.xlsx"
    rab.write_bytes(b"rab")
    nomenklatur.write_bytes(b"nomenklatur")
    active_path = tmp_path / "outputs/reports/active.json"
    active_path.parent.mkdir(parents=True)
    active_path.write_text(
        '{"dataset_id":"dataset-1","dataset_session_id":"dataset-1",'
        '"status":"committed","upload_state":"COMMITTED","files":['
        '{"filename":"RAB_2025_SD_RAB_IKU.xlsx",'
        '"path":"data/raw/excel_lakehouse/dataset-1/RAB_2025_SD_RAB_IKU.xlsx",'
        '"jenis_dataset":"nomenklatur"},'
        '{"filename":"Nomenklatur.xlsx",'
        '"path":"data/raw/excel_lakehouse/dataset-1/Nomenklatur.xlsx",'
        '"jenis_dataset":"nomenklatur"}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(excel_upload, "ACTIVE_EXCEL_DATASET_PATH", active_path)
    monkeypatch.setattr(app_module, "PORTAL_DIR", tmp_path / "portal")
    monkeypatch.setattr(app_module, "purge_stale_queued_runs", lambda _session: [])
    monkeypatch.setattr(app_module, "get_active_dag_run", lambda **_kwargs: None)
    monkeypatch.setattr(app_module, "trigger_dag", lambda **kwargs: {
        "dag_id": DAG_ID,
        "dag_run_id": "portal__run-repaired",
        "dataset_session_id": kwargs["dataset_session_id"],
        "pipeline_run_id": kwargs["pipeline_run_id"],
        "state": "queued",
    })

    response = create_app().test_client().post("/api/airflow/trigger", json={})

    assert response.status_code == 202
    assert response.get_json()["dag_run_id"] == "portal__run-repaired"


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
