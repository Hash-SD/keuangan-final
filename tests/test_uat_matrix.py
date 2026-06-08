import json
from pathlib import Path

from src.metrics.generate_uat import main as generate_uat


ROOT = Path(__file__).resolve().parents[1]


def test_uat_matrix_matches_report_score():
    generate_uat()
    summary = json.loads((ROOT / "outputs" / "uat" / "uat_score_summary.json").read_text(encoding="utf-8"))
    matrix = json.loads((ROOT / "outputs" / "uat" / "uat_matrix_summary.json").read_text(encoding="utf-8"))

    assert summary["average_score"] == 4.84
    assert summary["percentage"] == 96.8
    assert summary["category"] == "Sangat baik"
    assert len(matrix["items"]) == 5
    assert all("Gauge Chart" not in item["pertanyaan"] for item in matrix["items"])
