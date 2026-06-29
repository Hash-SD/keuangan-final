from __future__ import annotations

from typing import Any

import pandas as pd

from .files import read_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR


def excel_lakehouse_status() -> dict[str, Any]:
    metadata = read_json(DATA_DIR / "generated" / "excel_lakehouse_metadata.json") or {}
    pipeline_summary = read_json(OUTPUTS_DIR / "reports" / "pipeline_run_summary.json") or metadata
    outputs = metadata.get("outputs") or {}
    required = {
        "bronze_excel_cells": DATA_DIR / "generated" / "bronze" / "bronze_excel_cells.parquet",
        "silver_rab_items_flexible": DATA_DIR / "generated" / "silver" / "silver_rab_items_flexible.parquet",
        "silver_nomenklatur_detail": DATA_DIR / "generated" / "silver" / "silver_nomenklatur_detail.parquet",
        "silver_mapping": DATA_DIR / "generated" / "silver" / "silver_mapping.parquet",
        "silver_validation": DATA_DIR / "generated" / "silver" / "silver_validation.parquet",
        "fact_anggaran": DATA_DIR / "generated" / "gold" / "fact_anggaran.parquet",
    }
    artifacts = {
        name: {
            "available": path.exists(),
            "path": path.resolve().relative_to(ROOT_DIR.resolve()).as_posix() if path.exists() else path.as_posix(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        for name, path in required.items()
    }
    ready = all(item["available"] for item in artifacts.values())
    counts = {
        "bronze_cells": metadata.get("bronze_cells"),
        "silver_rab_items": metadata.get("silver_rab_items"),
        "nomenklatur_detail": metadata.get("silver_nomenklatur_detail"),
        "fact_anggaran_rows": metadata.get("fact_anggaran_rows"),
    }
    fact_summary: dict[str, Any] = {"total_jumlah": None, "total_weighted_iku": None}
    fact_path = required["fact_anggaran"]
    if fact_path.exists():
        try:
            fact = pd.read_parquet(fact_path, columns=["jumlah", "jumlah_weighted_iku"])
            fact_summary = {
                "total_jumlah": float(pd.to_numeric(fact["jumlah"], errors="coerce").fillna(0).sum()),
                "total_weighted_iku": float(pd.to_numeric(fact["jumlah_weighted_iku"], errors="coerce").fillna(0).sum()),
            }
        except Exception:
            fact_summary = {"total_jumlah": None, "total_weighted_iku": None}
    return {
        "status": "ready" if ready else "missing",
        "domain": "excel_lakehouse",
        "system_name": "SILARAS SD",
        "system_full_name": "Sistem Lakehouse Anggaran RAB dan IKU Sains Data",
        "excel_only": True,
        "counts": counts,
        "fact_anggaran": fact_summary,
        "metadata": metadata,
        "pipeline_summary": pipeline_summary,
        "artifacts": artifacts,
        "outputs": outputs,
    }
