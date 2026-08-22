from src.status.system_truth_status import build_system_truth_status
import json


def test_empty_state_has_no_final_numbers(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTAL_BACKEND_PORT", "65530")
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    monkeypatch.setenv("MINIO_API_PORT", "65532")

    truth = build_system_truth_status(tmp_path)

    assert truth["quality_gate"]["total_rows"]["value"] is None
    assert truth["quality_gate"]["status"] == "missing"
    assert truth["reconciliation"]["total_anggaran"]["value"] is None
    assert truth["uat"]["average_score"] is None
    assert truth["dashboard"]["status"] in {"not_started", "unreachable"}
    assert truth["services"]["superset"]["status"] == "unreachable"


def test_dashboard_with_only_historical_artifacts_is_not_current(tmp_path, monkeypatch):
    reports = tmp_path / "outputs" / "reports"
    reports.mkdir(parents=True)
    (reports / "active_excel_lakehouse_dataset.json").write_text(
        json.dumps({"status": "empty", "dataset_session_id": None, "files": []}),
        encoding="utf-8",
    )
    historical = {
        "status": "validated",
        "dataset_session_id": "old-dataset",
        "pipeline_run_id": "old-run",
        "dashboard_verification": {"status": "validated"},
        "dashboard_url": "http://example.test/dashboard/old",
    }
    (reports / "superset_excel_dashboard.json").write_text(json.dumps(historical), encoding="utf-8")
    (reports / "superset_excel_assets.json").write_text(json.dumps(historical), encoding="utf-8")
    monkeypatch.setattr(
        "src.status.system_truth_status._service_statuses",
        lambda _base: {"superset": {"status": "ready"}},
    )

    truth = build_system_truth_status(tmp_path)

    assert truth["dashboard"]["status"] == "not_available"
    assert truth["dashboard"]["scope"] == "historical"
    assert truth["dashboard"]["query_verified"] is False
