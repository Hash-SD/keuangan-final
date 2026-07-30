import json
from pathlib import Path

from src.metrics.generate_uat import main as generate_uat


ROOT = Path(__file__).resolve().parents[1]


def test_uat_matrix_matches_report_score():
    generate_uat()
    summary = json.loads((ROOT / "outputs" / "uat" / "uat_score_summary.json").read_text(encoding="utf-8"))
    matrix = json.loads((ROOT / "outputs" / "uat" / "uat_matrix_summary.json").read_text(encoding="utf-8"))

    assert summary["average_score"] == 5.0
    assert summary["percentage"] == 100.0
    assert summary["category"] == "Sangat baik"
    assert summary["respondent_count"] == 1
    assert summary["respondents"] == [{"nama": "Pak Tirta", "peran": "Kaprodi"}]
    assert summary["scope"] == "Dashboard analitik anggaran RAB/IKU"
    assert len(matrix["items"]) == 5
    assert all(item["responden"] == "Pak Tirta" for item in matrix["items"])
    assert all(item["peran_responden"] == "Kaprodi" for item in matrix["items"])
    assert all("Gauge Chart" not in item["pertanyaan"] for item in matrix["items"])
