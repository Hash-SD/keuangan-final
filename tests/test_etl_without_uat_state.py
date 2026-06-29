import json

import pandas as pd

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_etl_without_uat_keeps_uat_null(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    for relative in [
        "data/generated/bronze/bronze_excel_cells.parquet",
        "data/generated/silver/silver_rab_items_flexible.parquet",
        "data/generated/silver/silver_nomenklatur_detail.parquet",
        "data/generated/silver/silver_mapping.parquet",
        "data/generated/silver/silver_validation.parquet",
        "data/generated/gold/fact_anggaran.parquet",
    ]:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"item_id": "A", "jumlah": 100, "jumlah_weighted_iku": 100}]).to_parquet(path)
    _write_json(tmp_path / "outputs/reports/pipeline_count_validation.json", {"fact_anggaran_rows": 1})

    truth = build_system_truth_status(tmp_path)

    assert truth["layers"]["gold"]["status"] == "ready"
    assert truth["reconciliation"]["status"] == "validated"
    assert truth["uat"]["status"] == "missing"
    assert truth["uat"]["average_score"] is None
