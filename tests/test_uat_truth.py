from __future__ import annotations

import json

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_uat_requires_real_local_response_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_csv(tmp_path / "outputs/uat/uat_template.csv", ["indikator", "Navigation"])

    truth = build_system_truth_status(tmp_path)

    assert truth["uat"]["status"] == "manual_input_required"
    assert truth["uat"]["average_score"] is None


def test_uat_completed_from_local_response_file(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_csv(tmp_path / "outputs/uat/uat_template.csv", ["indikator", "Navigation"])
    _write_csv(tmp_path / "outputs/uat/uat_response.csv", ["responden,skor", "A,5"])
    _write_json(tmp_path / "outputs/uat/uat_score_summary.json", {"average_score": 5, "percentage": 100, "category": "Sangat baik", "respondent_count": 1})
    _write_json(tmp_path / "outputs/uat/uat_matrix_summary.json", {"items": []})

    truth = build_system_truth_status(tmp_path)

    assert truth["uat"]["status"] == "completed"
    assert truth["uat"]["average_score"] == 5
