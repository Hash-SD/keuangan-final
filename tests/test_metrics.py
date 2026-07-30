from pathlib import Path

import json
import os
from datetime import datetime, timezone

from src.metrics.pipeline_latency import compute_pipeline_latency
from src.metrics.data_freshness import compute_freshness

ROOT = Path(__file__).resolve().parents[1]


def test_pipeline_latency_uses_active_source_and_gold_artifacts(tmp_path, monkeypatch):
    source_time = datetime(2026, 6, 9, 1, 0, tzinfo=timezone.utc).timestamp()
    gold_time = datetime(2026, 6, 9, 1, 7, 30, tzinfo=timezone.utc).timestamp()
    raw_rab = tmp_path / "data/raw/excel_lakehouse/2025/upload-test/rab.xlsx"
    raw_nomenklatur = tmp_path / "data/raw/excel_lakehouse/2025/upload-test/nomenklatur.xlsx"
    for path in [raw_rab, raw_nomenklatur]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x", encoding="utf-8")
        os.utime(path, (source_time, source_time))

    pointer = {
        "status": "committed",
        "dataset_id": "excel-upload-test",
        "dataset_session_id": "excel-upload-test",
        "upload_committed_at": "2026-06-09T01:00:00+00:00",
        "files": [
            {"path": "data/raw/excel_lakehouse/2025/upload-test/rab.xlsx", "jenis_dataset": "rab"},
            {"path": "data/raw/excel_lakehouse/2025/upload-test/nomenklatur.xlsx", "jenis_dataset": "nomenklatur"},
        ],
    }
    pointer_path = tmp_path / "outputs/reports/active_excel_lakehouse_dataset.json"
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

    manifest = tmp_path / "outputs/reports/pipeline_runs/run-test.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"dataset_session_id":"excel-upload-test","pipeline_run_id":"run-test","upload_committed_at":"2026-06-09T01:00:00+00:00","gold_finished_at":"2026-06-09T01:07:30+00:00"}), encoding="utf-8")

    result = compute_pipeline_latency(base_dir=tmp_path, write_output=True)

    assert result["status"] == "validated"
    assert result["pipeline_latency_seconds"] == 450
    assert (tmp_path / "outputs/metrics/pipeline_latency.json").exists()


def test_pipeline_latency_does_not_fallback_when_run_timeline_is_incomplete(tmp_path):
    pointer = {
        "status": "committed",
        "dataset_id": "excel-upload-test",
        "dataset_session_id": "excel-upload-test",
        "upload_committed_at": "2026-06-09T01:00:00+00:00",
    }
    path = tmp_path / "outputs/reports/active_excel_lakehouse_dataset.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pointer), encoding="utf-8")

    result = compute_pipeline_latency(base_dir=tmp_path, write_output=False)

    assert result["status"] == "not_available"
    assert "gold_finished_at" in result["missing_fields"]


def test_freshness_requires_dashboard_verification_timestamp():
    result = compute_freshness({"dataset_session_id":"dataset-a","pipeline_run_id":"run-a","upload_committed_at":"2026-06-09T01:00:00+00:00","gold_finished_at":"2026-06-09T01:01:00+00:00"})
    assert result["status"] == "not_available"
    assert result["missing_fields"] == ["dashboard_verified_at"]
