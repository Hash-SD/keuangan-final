from __future__ import annotations

import json

from src.storage import excel_storage_manifest
from src.status.system_truth_status import build_system_truth_status


def test_storage_manifest_is_not_canonical_without_run_identity(monkeypatch):
    monkeypatch.setattr(excel_storage_manifest, "PIPELINE_RUN_ID", None)
    monkeypatch.setattr(excel_storage_manifest, "DATASET_SESSION_ID", None)
    result = excel_storage_manifest.build_excel_storage_manifest()
    assert result["status"] == "not_ready"
    assert result["entries"] == []


def test_dashboard_status_cannot_be_created_from_stale_assets(tmp_path, monkeypatch):
    reports = tmp_path / "outputs" / "reports"
    reports.mkdir(parents=True)
    (reports / "superset_excel_assets.json").write_text(json.dumps({"dataset_id": 1}), encoding="utf-8")
    (reports / "superset_excel_dashboard.json").write_text(json.dumps({"dashboard_url": "stale"}), encoding="utf-8")
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    truth = build_system_truth_status(tmp_path)
    assert truth["dashboard"]["status"] == "not_ready"
    assert truth["dashboard"]["query_verified"] is False
