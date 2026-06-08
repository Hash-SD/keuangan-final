from pathlib import Path

import json


ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_summary_exists():
    summary = json.loads((ROOT / "data" / "quarantine" / "logs" / "quality_gate_summary.json").read_text(encoding="utf-8"))
    context_path = ROOT / "outputs" / "reports" / "active_runtime_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else {}
    assert summary["total_rows"] == context.get("dummy_transaction_rows", 800)
    assert summary["rejected_rows"] == context.get("dummy_invalid_rows", 16)
