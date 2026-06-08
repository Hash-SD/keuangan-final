from __future__ import annotations

import json

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_uat_dummy_response_is_not_final(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_csv(tmp_path / "outputs/uat/uat_template.csv", ["indikator", "Navigation"])
    _write_csv(tmp_path / "outputs/uat/uat_dummy_response.csv", ["responden,skor", "A,5"])
    _write_json(tmp_path / "outputs/uat/uat_score_summary.json", {"average_score": 4.84, "percentage": 96.8, "category": "Sangat baik", "respondent_count": 1})
    _write_json(tmp_path / "outputs/uat/uat_matrix_summary.json", {"items": []})

    truth = build_system_truth_status(tmp_path)

    assert truth["uat"]["status"] == "manual_input_required"
    assert truth["uat"]["average_score"] is None
    assert truth["uat"]["dummy_responses_available"] is True
