from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .files import read_json
from .paths import DATA_DIR, OUTPUTS_DIR, SILVER_RAB_PATH


def _count_rows(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    except OSError:
        return None


def lakehouse_summary() -> dict[str, Any]:
    bronze_metadata = DATA_DIR / "generated" / "bronze" / "ingestion_metadata.json"
    silver_files = [
        DATA_DIR / "generated" / "silver" / "fact_piutang_ukt_prodi.csv",
        DATA_DIR / "generated" / "silver" / "transactions_clean.csv",
        SILVER_RAB_PATH,
    ]
    gold_fact = DATA_DIR / "generated" / "gold" / "fact_piutang_ukt_prodi.csv"
    gold_dashboard = DATA_DIR / "generated" / "gold" / "vw_dashboard_piutang_ukt.csv"
    reconcile = read_json(OUTPUTS_DIR / "metrics" / "reconcile_control_total.json")
    gold_valid = bool(reconcile and str(reconcile.get("status", "")).lower() == "pass")

    return {
        "bronze": {
            "status": "ready" if bronze_metadata.exists() else "waiting",
            "description": "Raw data PDF, CSV, dan Excel tersimpan apa adanya.",
            "files": 1 if bronze_metadata.exists() else 0,
            "metadata": "data/generated/bronze/ingestion_metadata.json",
        },
        "silver": {
            "status": "ready" if all(path.exists() for path in silver_files) else "waiting",
            "description": "Data dibersihkan, distandarkan, dan Excel RAB di-unpivot.",
            "tables": [path.name for path in silver_files if path.exists()],
        },
        "gold": {
            "status": "ready" if gold_fact.exists() and gold_dashboard.exists() else "waiting",
            "valid": gold_valid,
            "description": "Star Schema siap dibaca Trino dan Superset.",
            "fact_rows": _count_rows(gold_fact),
            "dashboard_view": gold_dashboard.exists(),
            "validation": reconcile,
        },
    }
