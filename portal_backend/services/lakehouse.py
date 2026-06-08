from __future__ import annotations

from typing import Any

from src.status.system_truth_status import build_system_truth_status


def lakehouse_summary() -> dict[str, Any]:
    truth = build_system_truth_status(write_outputs=True)
    layers = truth["layers"]
    reconcile = truth["reconciliation"]
    return {
        "bronze": {
            "status": layers["bronze"]["status"],
            "description": "Raw data PDF, CSV, dan Excel tersimpan apa adanya.",
            "files": layers["bronze"]["file_count"],
            "metadata": layers["bronze"]["existing"],
        },
        "silver": {
            "status": layers["silver"]["status"],
            "description": "Data dibersihkan, distandarkan, dan Excel RAB di-unpivot.",
            "tables": layers["silver"]["existing"],
        },
        "gold": {
            "status": layers["gold"]["status"],
            "valid": reconcile["status"] == "validated",
            "description": "Star Schema siap dibaca Trino dan Superset.",
            "fact_rows": None,
            "dashboard_view": any("vw_dashboard_piutang_ukt.csv" in item for item in layers["gold"]["existing"]),
            "validation": reconcile,
        },
        "storage": {
            "mapping": truth["storage"].get("mapping"),
            "manifest": truth["storage"].get("manifest"),
            "status": truth["storage"]["status"],
        },
        "truth": truth,
    }
