from __future__ import annotations

from typing import Any

import pandas as pd

from src.gold.contract import FACT_COLUMNS, validate_fact_columns


REQUIRED_GOLD_COLUMNS = {
    "item_id",
    "run_id",
    "dataset_session_id",
    "tahun",
    "prodi",
    "kegiatan",
    "uraian_detail",
    "jumlah",
    "allocation_weight",
    "jumlah_weighted_iku",
    "source_file",
    "source_sheet",
    "source_row",
    "created_at",
}

FORBIDDEN_GOLD_COLUMNS = {
    "periode",
    "pipeline_run_id",
    "nominal_piutang_rp",
    "tahun_akademik",
    "nama_debitur",
    "nim",
}


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column, pd.Series(index=frame.index, dtype=float)), errors="coerce")


def evaluate_gold_quality(fact: pd.DataFrame, dataset_session_id: str, pipeline_run_id: str) -> dict[str, Any]:
    """Return blocking annual Gold checks for one isolated dataset/run."""

    errors: list[str] = []
    warnings: list[str] = []
    if fact.empty:
        errors.append("gold_output_empty")
        return {"status": "FAILED", "blocking_errors": errors, "warnings": warnings, "metrics": {"rows": 0}}

    schema = validate_fact_columns(fact.columns)
    if schema["missing"] or schema["unexpected"]:
        errors.append("gold_schema_mismatch")
    missing_required = sorted(REQUIRED_GOLD_COLUMNS - set(fact.columns))
    if missing_required:
        errors.append("missing_required_gold_columns")
    forbidden = sorted(FORBIDDEN_GOLD_COLUMNS.intersection(fact.columns))
    if forbidden:
        errors.append("forbidden_gold_columns_present")

    identity_columns = [column for column in ("dataset_session_id", "run_id", "item_id", "tahun") if column in fact.columns]
    if "dataset_session_id" in fact and not fact["dataset_session_id"].astype(str).eq(dataset_session_id).all():
        errors.append("dataset_session_id_mismatch")
    if "run_id" in fact and not fact["run_id"].astype(str).eq(pipeline_run_id).all():
        errors.append("run_id_mismatch")
    if "tahun" in fact and fact["tahun"].isna().any():
        errors.append("tahun_missing")
    if identity_columns:
        required_nulls = int(fact[identity_columns].isna().sum().sum())
    else:
        required_nulls = len(fact)
    if required_nulls:
        errors.append("lineage_or_required_attributes_incomplete")

    grain = [column for column in ("dataset_session_id", "run_id", "item_id", "kode_iku") if column in fact.columns]
    duplicate_rows = int(fact.duplicated(grain, keep=False).sum()) if grain else len(fact)
    if duplicate_rows:
        errors.append("duplicate_fact_rows")

    text = fact.get("uraian_detail", pd.Series("", index=fact.index)).fillna("").astype(str).str.lower()
    if text.str.contains(r"\b(?:subtotal|grand total|total)\b", regex=True).any():
        errors.append("header_or_total_like_row_in_gold")

    amounts = _numeric(fact, "jumlah")
    weights = _numeric(fact, "allocation_weight")
    weighted = _numeric(fact, "jumlah_weighted_iku")
    if amounts.isna().any() or weights.isna().any() or weighted.isna().any() or ((weights < 0) | (weights > 1)).any():
        errors.append("invalid_numeric_or_allocation_weight")
    elif not ((amounts * weights - weighted).abs() <= 0.01).all():
        errors.append("weighted_formula_inconsistent")

    allocation_group = [column for column in ("dataset_session_id", "run_id", "item_id") if column in fact.columns]
    allocation_sums = fact.groupby(allocation_group, dropna=False)["allocation_weight"].sum() if allocation_group else pd.Series(dtype=float)
    invalid_allocations = int((allocation_sums.sub(1).abs() > 0.000001).sum()) if not allocation_sums.empty else 0
    if invalid_allocations:
        errors.append("allocation_weight_not_one_per_item")

    item_totals = fact.drop_duplicates(allocation_group)["jumlah"].sum() if allocation_group else amounts.sum()
    weighted_total = float(weighted.fillna(0).sum())
    annual_reconciliation_status = "VALIDATED" if abs(float(item_totals) - weighted_total) <= 0.01 else "CHECK"
    if annual_reconciliation_status != "VALIDATED":
        errors.append("annual_reconciliation_failed")

    return {
        "status": "PASSED" if not errors else "FAILED",
        "blocking_errors": errors,
        "warnings": warnings,
        "metrics": {
            "rows": int(len(fact)),
            "duplicate_fact_rows": duplicate_rows,
            "required_nulls": required_nulls,
            "invalid_allocations": invalid_allocations,
            "gold_row_count": int(len(fact)),
            "gold_weighted_total": weighted_total,
            "gold_item_total": float(item_totals),
            "annual_reconciliation_status": annual_reconciliation_status,
            "schema_columns": list(FACT_COLUMNS),
            "forbidden_columns": forbidden,
        },
    }
