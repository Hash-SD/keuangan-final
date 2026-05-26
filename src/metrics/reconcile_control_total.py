from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR


def reconcile() -> dict:
    fact = pd.read_csv(GENERATED_DIR / "gold" / "fact_piutang_ukt_prodi.csv")
    org = pd.read_csv(GENERATED_DIR / "gold" / "dim_organisasi.csv")
    data = fact.merge(org, on="organisasi_key")
    sains = data[data["nama_prodi"] == "Sains Data"]
    result = {
        "total_piutang": int(sains["nominal_piutang_rp"].sum()),
        "jumlah_penunggak": int(sains["jumlah_mhs_penunggak"].sum()),
        "target_total_piutang": 31_250_000,
        "target_jumlah_penunggak": 15,
    }
    result["status"] = "pass" if result["total_piutang"] == result["target_total_piutang"] and result["jumlah_penunggak"] == result["target_jumlah_penunggak"] else "fail"
    write_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json", result)
    return result


if __name__ == "__main__":
    print(reconcile())

