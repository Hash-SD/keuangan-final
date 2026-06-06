from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR
from src.common.runtime_config import configured_batch_id, get_runtime_config


def main() -> None:
    config = get_runtime_config()
    fact = pd.read_csv(GENERATED_DIR / "gold" / "fact_piutang_ukt_prodi.csv")
    reconcile = json.loads((OUTPUTS_DIR / "metrics" / "reconcile_control_total.json").read_text(encoding="utf-8"))
    completeness = float(100 * fact.notna().mean().mean())
    validity = float(100 * (pd.to_numeric(fact["nominal_piutang_rp"], errors="coerce").notna().mean()))
    consistency = 100.0 if fact["piutang_key"].is_unique else 0.0
    accuracy = 100.0 if reconcile["status"] == "pass" else 0.0
    score = (completeness + validity + consistency + accuracy) / 4
    write_json(
        OUTPUTS_DIR / "metrics" / "data_quality_score.json",
        {
            "batch_id": configured_batch_id(),
            "target_prodi": config.target_prodi,
            "target_tahun_akademik": config.target_tahun_akademik,
            "target_label": config.target_label,
            "completeness": round(completeness, 2),
            "validity": round(validity, 2),
            "consistency": round(consistency, 2),
            "accuracy": round(accuracy, 2),
            "data_quality_score": round(score, 2),
        },
    )


if __name__ == "__main__":
    main()
