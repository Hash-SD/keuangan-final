from pathlib import Path

import json
import os
from datetime import datetime, timezone

from src.metrics.pipeline_latency import compute_pipeline_latency

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
        "created_at": "2026-06-09T01:00:00+00:00",
        "files": [
            {"path": "data/raw/excel_lakehouse/2025/upload-test/rab.xlsx", "jenis_dataset": "rab"},
            {"path": "data/raw/excel_lakehouse/2025/upload-test/nomenklatur.xlsx", "jenis_dataset": "nomenklatur"},
        ],
    }
    pointer_path = tmp_path / "outputs/reports/active_excel_lakehouse_dataset.json"
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_text(json.dumps(pointer), encoding="utf-8")

    for relative in ["data/generated/gold/fact_anggaran.csv", "data/generated/gold/vw_dashboard_iku_anggaran.csv", "data/generated/gold/vw_dashboard_detail_item.csv", "data/generated/excel_lakehouse_metadata.json"]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"dataset_id": "excel-upload-test"}) if path.suffix == ".json" else "x", encoding="utf-8")
        os.utime(path, (gold_time, gold_time))

    result = compute_pipeline_latency(base_dir=tmp_path, write_output=True)

    assert result["status"] == "validated"
    assert result["source_basis"] == "active_excel_lakehouse_dataset"
    assert result["pipeline_latency_seconds"] == 450
    assert (tmp_path / "outputs/metrics/pipeline_latency.json").exists()
