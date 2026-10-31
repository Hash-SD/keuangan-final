from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.paths import GENERATED_DIR, OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso


def _read(path: Path) -> pd.DataFrame:
    if path.suffix == ".parquet" and path.exists():
        return pd.read_parquet(path)
    csv_path = path.with_suffix(".csv")
    if csv_path.exists():
        return pd.read_csv(csv_path)
    return pd.DataFrame()


def validate_counts() -> dict:
    bronze = _read(GENERATED_DIR / "bronze" / "bronze_excel_cells.parquet")
    silver = _read(GENERATED_DIR / "silver" / "silver_rab_items_flexible.parquet")
    nomenklatur = _read(GENERATED_DIR / "silver" / "silver_nomenklatur_detail.parquet")
    fact = _read(GENERATED_DIR / "gold" / "fact_anggaran.parquet")

    fact_key_cols = [col for col in ["item_id", "source_file", "source_sheet", "source_row"] if col in fact.columns]
    duplicate_fact_rows = int(fact.duplicated(subset=fact_key_cols).sum()) if fact_key_cols else 0
    total_like = 0
    if "uraian_detail" in fact.columns:
        total_like = int(fact["uraian_detail"].fillna("").astype(str).str.contains(r"\b(?:total|subtotal|jumlah)\b", case=False, regex=True).sum())
    header_like = 0
    if "uraian_detail" in fact.columns:
        header_like = int(fact["uraian_detail"].fillna("").astype(str).str.fullmatch(r"(?i)\s*(uraian|no|jumlah|harga|qty|satuan)\s*").sum())
    weighted_ok = True
    if {"jumlah", "allocation_weight", "jumlah_weighted_iku"}.issubset(fact.columns):
        expected = pd.to_numeric(fact["jumlah"], errors="coerce") * pd.to_numeric(fact["allocation_weight"], errors="coerce")
        actual = pd.to_numeric(fact["jumlah_weighted_iku"], errors="coerce")
        weighted_ok = bool(((expected.fillna(0) - actual.fillna(0)).abs() < 0.0001).all())

    result = {
        "generated_at": utc_now_iso(),
        "definitions": {
            "bronze_cells": "Rows in bronze_excel_cells; includes cells with value, formula, fill color, or merged-range lineage.",
            "silver_rab_candidate_rows": "Parsed RAB-like rows before downstream mapping curation.",
            "silver_rab_items_flexible": "Current fact-ready Silver item rows after parser excludes headers, totals, and empty rows.",
            "silver_nomenklatur_detail": "Nomenklatur rows where one row equals one detail kegiatan with inherited hierarchy.",
            "fact_anggaran_rows": "Gold rows at item x IKU allocation grain. With one IKU or unmapped IKU this equals item rows; multi-IKU expands rows with allocation_weight.",
        },
        "counts": {
            "bronze_cells": int(len(bronze)),
            "silver_rab_candidate_rows": int(len(silver)),
            "silver_rab_items_flexible": int(len(silver)),
            "silver_nomenklatur_detail": int(len(nomenklatur)),
            "fact_anggaran_rows": int(len(fact)),
            "fact_unique_item_ids": int(fact["item_id"].nunique()) if "item_id" in fact.columns else 0,
            "fact_unique_item_iku_rows": int(fact.drop_duplicates(subset=fact_key_cols).shape[0]) if fact_key_cols else 0,
        },
        "quality_checks": {
            "duplicate_fact_rows": duplicate_fact_rows,
            "fact_contains_total_like_rows": total_like,
            "fact_contains_header_like_rows": header_like,
            "weighted_amount_formula_ok": weighted_ok,
            "fact_row_grain": "item_x_iku_allocation",
            "rab_main_and_detail_duplication_policy": "Parser excludes total/subtotal rows; duplicate check uses item_id + IKU/source lineage. Sheet-level source lineage remains available for audit.",
        },
        "status": "validated" if duplicate_fact_rows == 0 and total_like == 0 and header_like == 0 and weighted_ok else "review_required",
    }
    return result


def main() -> None:
    result = validate_counts()
    reports = OUTPUTS_DIR / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "pipeline_count_validation.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    doc = ROOT_DIR / "docs" / "brainstorming" / "pipeline_count_validation.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(
        "# Pipeline Count Validation\n\n"
        f"Status: `{result['status']}`\n\n"
        "## Counts\n\n"
        + "\n".join(f"- `{key}`: `{value}`" for key, value in result["counts"].items())
        + "\n\n## Definitions\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in result["definitions"].items())
        + "\n\n## Quality Checks\n\n"
        + "\n".join(f"- `{key}`: `{value}`" for key, value in result["quality_checks"].items())
        + "\n",
        encoding="utf-8",
    )
    print(result)


if __name__ == "__main__":
    main()
