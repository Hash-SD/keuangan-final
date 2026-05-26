from pathlib import Path

import json


ROOT = Path(__file__).resolve().parents[1]


def test_data_quality_score_perfect_for_controlled_dummy_data():
    score = json.loads((ROOT / "outputs" / "metrics" / "data_quality_score.json").read_text(encoding="utf-8"))
    assert score["data_quality_score"] == 100.0

