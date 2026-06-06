from pathlib import Path

import json


ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_passes():
    result = json.loads((ROOT / "outputs" / "metrics" / "reconcile_control_total.json").read_text(encoding="utf-8"))
    assert result["status"] == "pass"
    assert result["target_prodi"] == "Sains Data"
    assert result["target_tahun_akademik"] == "2023/2024"
    assert result["total_piutang"] == 31_250_000
    assert result["jumlah_penunggak"] == 15
