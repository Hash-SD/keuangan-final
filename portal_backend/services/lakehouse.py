from __future__ import annotations

from typing import Any
import pandas as pd

from .paths import DATA_DIR

from src.status.system_truth_status import build_system_truth_status


def lakehouse_summary() -> dict[str, Any]:
    truth = build_system_truth_status(write_outputs=True)
    layers = truth["layers"]
    reconcile = truth["reconciliation"]
    fact_anggaran_path = DATA_DIR / "generated" / "gold" / "fact_anggaran.csv"
    fact_anggaran_rows = None
    fact_anggaran_total = None
    if fact_anggaran_path.exists():
        try:
            fact_anggaran = pd.read_csv(fact_anggaran_path)
            fact_anggaran_rows = int(len(fact_anggaran))
            fact_anggaran_total = float(pd.to_numeric(fact_anggaran.get("jumlah_weighted_iku"), errors="coerce").sum())
        except Exception:
            fact_anggaran_rows = None
    return {
        "bronze": {
            "status": layers["bronze"]["status"],
            "description": "Bronze cell-level dari workbook Excel RAB/RPD/IKU/Nomenklatur.",
            "files": layers["bronze"]["file_count"],
            "metadata": layers["bronze"]["existing"],
        },
        "silver": {
            "status": layers["silver"]["status"],
            "description": "Normalisasi fleksibel item RAB, nomenklatur, mapping, dan validasi.",
            "tables": layers["silver"]["existing"],
        },
        "gold": {
            "status": layers["gold"]["status"],
            "valid": reconcile["status"] == "validated",
            "description": "Single fact table fact_anggaran siap dibaca Trino, Postgres, dan Superset.",
            "fact_rows": fact_anggaran_rows,
            "fact_anggaran_total_weighted": fact_anggaran_total,
            "dashboard_view": any("fact_anggaran.csv" in item for item in layers["gold"]["existing"]),
            "validation": reconcile,
        },
        "storage": {
            "mapping": truth["storage"].get("mapping"),
            "manifest": truth["storage"].get("manifest"),
            "status": truth["storage"]["status"],
        },
        "truth": truth,
    }
