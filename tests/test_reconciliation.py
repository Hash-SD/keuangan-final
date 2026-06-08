from pathlib import Path

import json


ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_passes():
    result = json.loads((ROOT / "outputs" / "metrics" / "reconcile_control_total.json").read_text(encoding="utf-8"))
    context_path = ROOT / "outputs" / "reports" / "active_runtime_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else {}
    assert result["status"] == "pass"
    assert result["target_prodi"] == context.get("target_prodi", "Sains Data")
    assert result["target_tahun_akademik"] == context.get("target_tahun_akademik", "2023/2024")
    assert result["target_total_piutang"] == result["total_piutang"]
    assert result["target_jumlah_penunggak"] == result["jumlah_penunggak"]
