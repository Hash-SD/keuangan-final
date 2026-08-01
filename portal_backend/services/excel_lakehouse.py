from __future__ import annotations

from typing import Any

import pandas as pd

from .files import read_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR


_fact_summary_cache: tuple[float, dict[str, Any]] | None = None


def _get_cached_fact_summary(fact_parquet: Path, fact_csv: Path) -> dict[str, Any]:
    """⚡ Bolt Optimization: Fast mtime-based cache for fact_anggaran summary.
    Eliminates redundant disk I/O on polling requests when underlying files have not changed.
    """
    global _fact_summary_cache

    mtime_parquet = fact_parquet.stat().st_mtime if fact_parquet.exists() else 0.0
    mtime_csv = fact_csv.stat().st_mtime if fact_csv.exists() else 0.0
    current_mtime = (str(fact_parquet), str(fact_csv), mtime_parquet, mtime_csv)

    if _fact_summary_cache is not None:
        cached_mtime, cached_result = _fact_summary_cache
        if cached_mtime == current_mtime:
            return cached_result

    fact_df = None
    if fact_parquet.exists():
        try:
            fact_df = pd.read_parquet(fact_parquet, columns=["item_id", "jumlah", "jumlah_weighted_iku"])
        except Exception:
            fact_df = None

    if fact_df is None and fact_csv.exists():
        try:
            fact_df = pd.read_csv(fact_csv)
        except Exception:
            fact_df = None

    fact_summary: dict[str, Any] = {"total_jumlah": None, "total_weighted_iku": None}
    if fact_df is not None and not fact_df.empty:
        distinct_fact = fact_df.drop_duplicates(subset=["item_id"]) if "item_id" in fact_df.columns else fact_df
        fact_summary = {
            "total_jumlah": float(pd.to_numeric(distinct_fact["jumlah"], errors="coerce").fillna(0).sum()),
            "total_weighted_iku": float(pd.to_numeric(fact_df["jumlah_weighted_iku"], errors="coerce").fillna(0).sum()),
        }

    _fact_summary_cache = (current_mtime, fact_summary)
    return fact_summary


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
    if not ready:
        counts = {key: None for key in counts}

    fact_parquet = required["fact_anggaran"]
    fact_csv = DATA_DIR / "generated" / "gold" / "fact_anggaran.csv"
    fact_summary = _get_cached_fact_summary(fact_parquet, fact_csv)
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
