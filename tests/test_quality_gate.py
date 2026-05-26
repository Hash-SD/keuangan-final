from pathlib import Path

import json


ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_summary_exists():
    summary = json.loads((ROOT / "data" / "quarantine" / "logs" / "quality_gate_summary.json").read_text(encoding="utf-8"))
    assert summary["total_rows"] == 800
    assert summary["rejected_rows"] == 16

