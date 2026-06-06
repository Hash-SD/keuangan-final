from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR
from src.common.runtime_config import get_runtime_config


def reconcile() -> dict:
    config = get_runtime_config()
    fact = pd.read_csv(GENERATED_DIR / "gold" / "fact_piutang_ukt_prodi.csv")
    org = pd.read_csv(GENERATED_DIR / "gold" / "dim_organisasi.csv")
    data = fact.merge(org, on="organisasi_key")
    target_data = data[data["nama_prodi"] == config.target_prodi]
    total_piutang = int(target_data["nominal_piutang_rp"].sum())
    jumlah_penunggak = int(target_data["jumlah_mhs_penunggak"].sum())
    target_total = config.target_total_piutang
    target_penunggak = config.target_jumlah_penunggak
    observed_only = target_total is None and target_penunggak is None
    result = {
        "target_prodi": config.target_prodi,
        "total_piutang": total_piutang,
        "jumlah_penunggak": jumlah_penunggak,
        "target_total_piutang": target_total if target_total is not None else total_piutang,
        "target_jumlah_penunggak": target_penunggak if target_penunggak is not None else jumlah_penunggak,
        "validation_mode": "explicit_target" if not observed_only else "observed_only",
    }
    result["status"] = "pass" if (
        (target_total is None or total_piutang == target_total)
        and (target_penunggak is None or jumlah_penunggak == target_penunggak)
    ) else "fail"
    write_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json", result)
    return result


if __name__ == "__main__":
    print(reconcile())
