import json

import pandas as pd

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_completed_state_uses_available_artifact_values(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_json(tmp_path / "outputs/uat/uat_score_summary.json", {"average_score": 4.84, "percentage": 96.8, "category": "Sangat baik", "respondent_count": 5})
    _write_json(tmp_path / "outputs/uat/uat_matrix_summary.json", {"items": []})
    _write_csv(tmp_path / "outputs/uat/uat_template.csv", ["indikator", "Navigation"])
    _write_csv(tmp_path / "outputs/uat/uat_response.csv", ["responden,skor", "A,5"])
    fact_path = tmp_path / "data/generated/gold/fact_anggaran.parquet"
    fact_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {"item_id": "A", "jumlah": 10_000_000, "jumlah_weighted_iku": 5_000_000},
            {"item_id": "B", "jumlah": 21_250_000, "jumlah_weighted_iku": 26_250_000},
        ]
    ).to_parquet(fact_path)
    _write_json(tmp_path / "outputs/reports/pipeline_count_validation.json", {"fact_anggaran_rows": 2})

    truth = build_system_truth_status(tmp_path)

    assert truth["uat"]["status"] == "completed"
    assert truth["uat"]["average_score"] == 4.84
    assert truth["quality_gate"]["status"] == "validated"
    assert truth["quality_gate"]["valid_rows"]["value"] == 2
    assert truth["reconciliation"]["total_anggaran"]["value"] == 31_250_000
