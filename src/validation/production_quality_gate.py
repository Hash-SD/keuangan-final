from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_GOLD_COLUMNS = {
    "item_id", "run_id", "dataset_session_id", "tahun", "prodi", "kegiatan",
    "uraian_detail", "jumlah", "allocation_weight", "jumlah_weighted_iku",
    "source_file", "source_sheet", "source_row", "created_at",
}


def evaluate_gold_quality(fact: pd.DataFrame, dataset_session_id: str, pipeline_run_id: str) -> dict[str, Any]:
    """Return blocking production gate results for one isolated Gold run."""
    errors: list[str] = []
    if fact.empty:
        errors.append("gold_output_empty")
        return {"status": "FAILED", "blocking_errors": errors, "warnings": [], "metrics": {"rows": 0}}
    missing_columns = sorted(REQUIRED_GOLD_COLUMNS - set(fact.columns))
    if missing_columns:
        errors.append("missing_required_gold_columns")
    required_nulls = int(fact[[column for column in REQUIRED_GOLD_COLUMNS if column in fact.columns]].isna().sum().sum())
    if required_nulls:
        errors.append("lineage_or_required_attributes_incomplete")
    if "dataset_session_id" in fact and not fact["dataset_session_id"].astype(str).eq(dataset_session_id).all():
        errors.append("dataset_session_id_mismatch")
    if "run_id" in fact and not fact["run_id"].astype(str).eq(pipeline_run_id).all():
        errors.append("pipeline_run_id_mismatch")
    grain = [column for column in ("item_id", "kode_iku") if column in fact.columns]
    duplicate_rows = int(fact.duplicated(grain, keep=False).sum()) if grain else len(fact)
    if duplicate_rows:
        errors.append("duplicate_fact_rows")
    text = fact.get("uraian_detail", pd.Series("", index=fact.index)).fillna("").astype(str).str.lower()
    if text.str.contains(r"\b(?:subtotal|grand total|total)\b", regex=True).any():
        errors.append("header_or_total_like_row_in_gold")
    amounts = pd.to_numeric(fact.get("jumlah"), errors="coerce")
    weights = pd.to_numeric(fact.get("allocation_weight"), errors="coerce")
    weighted = pd.to_numeric(fact.get("jumlah_weighted_iku"), errors="coerce")
    if amounts.isna().any() or weights.isna().any() or weighted.isna().any() or ((weights < 0) | (weights > 1)).any():
        errors.append("invalid_numeric_or_allocation_weight")
    elif not ((amounts * weights - weighted).abs() <= 0.01).all():
        errors.append("weighted_formula_inconsistent")
    return {
        "status": "PASSED" if not errors else "FAILED",
        "blocking_errors": errors,
        "warnings": [],
        "metrics": {"rows": int(len(fact)), "duplicate_fact_rows": duplicate_rows, "required_nulls": required_nulls},
    }
