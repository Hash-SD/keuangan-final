from __future__ import annotations

import os
import sys
import uuid
import json
import shutil
import re
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, GENERATED_DIR, OUTPUTS_DIR, RAW_DIR, ensure_parent
from src.common.runtime_paths import active_dataset_pointer, active_period_metadata, raw_rab_path
from src.common.time_utils import utc_now_iso
from src.excel_ingestion.excel_cell_extractor import ExcelSource, extract_excel_cells
from src.gold.fact_anggaran import build_fact_anggaran
from src.mapping.flexible_mapping import build_mapping_table
from src.parser_flexible.nomenklatur_parser import parse_nomenklatur_workbook
from src.parser_flexible.rab_parser import parse_rab_workbook
from src.transformations.budget_cleaning import clean_and_enrich_budget_items


REPO_ROOT = Path(__file__).resolve().parents[2]
EXCEL_EXTENSIONS = {".xlsx", ".xlsm", ".xltx", ".xltm"}


def _session_id() -> str:
    pointer = active_dataset_pointer() or {}
    return Path(str(pointer.get("session_id") or "excel-lakehouse")).name or "excel-lakehouse"


def _split_env_paths(value: str | None) -> list[Path]:
    if not value:
        return []
    return [Path(item.strip()) for item in value.split(";") if item.strip()]


def _resolve_repo_path(path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def _infer_year_from_filename(path: Path, default: object = None) -> str:
    match = re.search(r"\b(20\d{2})\b", path.name)
    if match:
        return match.group(1)
    if "nomenklatur" in path.name.lower():
        return "2025"
    return str(default or "")


def _infer_period_from_filename(path: Path, default: object = None) -> str | None:
    name = path.name.lower()
    if "jan" in name or "jun" in name:
        return "Jan-Jun"
    if "jul" in name or "des" in name or "dec" in name:
        return "Jul-Des"
    return str(default) if default else None


def _excel_source(path: Path, prodi: str, tahun_input: object = None, periode: object = None, jenis_dataset: object = None) -> ExcelSource:
    resolved = _resolve_repo_path(path)
    return ExcelSource(
        path=resolved,
        tahun_input=_infer_year_from_filename(resolved, tahun_input),
        periode=_infer_period_from_filename(resolved, periode),
        prodi=prodi,
        jenis_dataset=str(jenis_dataset or _dataset_kind(resolved)),
    )


def _uploaded_sample_kind(path: Path) -> str | None:
    name = path.name.lower()
    if "nomenklatur" in name:
        return "nomenklatur"
    if "rencana anggaran prodi sains data tahun 2024" in name:
        return "rab_2024"
    if "rab 2025" in name or "rab_2025" in name or "2025 sd rab iku" in name:
        return "rab_2025"
    if "2023" in name and ("jan" in name or "jun" in name):
        return "rab_2023_jan_jun"
    if "2023" in name and ("jul" in name or "des" in name or "dec" in name):
        return "rab_2023_jul_des"
    return None


def _discover_uploaded_multiyear_bundle() -> list[Path]:
    raw_root = DATA_DIR / "raw" / "excel_lakehouse"
    if not raw_root.exists():
        return []
    order = ["rab_2025", "nomenklatur", "rab_2024", "rab_2023_jan_jun", "rab_2023_jul_des"]
    best: tuple[int, float, dict[str, Path]] | None = None
    for directory in raw_root.rglob("*"):
        if not directory.is_dir():
            continue
        if any(part.lower() in {"test-session", "synthetic-session"} for part in directory.parts):
            continue
        files_by_kind: dict[str, Path] = {}
        for path in sorted(directory.iterdir()):
            if path.suffix.lower() not in EXCEL_EXTENSIONS or not path.is_file():
                continue
            kind = _uploaded_sample_kind(path)
            if kind and kind not in files_by_kind:
                files_by_kind[kind] = path
        if not {"nomenklatur", "rab_2025"}.issubset(files_by_kind):
            continue
        years_covered = sum(1 for kind in ("rab_2023_jan_jun", "rab_2023_jul_des", "rab_2024", "rab_2025") if kind in files_by_kind)
        score = len(files_by_kind) * 10 + years_covered
        newest = max(path.stat().st_mtime for path in files_by_kind.values())
        if best is None or (score, newest) > (best[0], best[1]):
            best = (score, newest, files_by_kind)
    if best is None:
        return []
    return [best[2][kind] for kind in order if kind in best[2]]


def discover_excel_sources() -> list[ExcelSource]:
    pointer = active_dataset_pointer() or {}
    excel_pointer_path = REPO_ROOT / "outputs" / "reports" / "active_excel_lakehouse_dataset.json"
    excel_pointer = {}
    if excel_pointer_path.exists():
        try:
            excel_pointer = json.loads(excel_pointer_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            excel_pointer = {}
    metadata = active_period_metadata()
    prodi = excel_pointer.get("prodi") or pointer.get("target_prodi") or metadata.get("target_prodi") or "Sains Data"
    tahun_input = excel_pointer.get("tahun_input") or pointer.get("tahun_anggaran") or metadata.get("target_tahun_anggaran")
    paths: list[Path] = []
    env_paths = _split_env_paths(os.getenv("FINANCE_EXCEL_FILES"))
    paths.extend(env_paths)
    if env_paths:
        return [_excel_source(path, prodi, tahun_input=tahun_input) for path in paths if _resolve_repo_path(path).exists()]

    if isinstance(excel_pointer.get("files"), list):
        paths.extend(Path(str(item.get("path") or item)) for item in excel_pointer["files"])
        pointer_paths = [_resolve_repo_path(path) for path in paths]
        pointer_sources = [
            ExcelSource(
                path=path,
                tahun_input=_infer_year_from_filename(path, tahun_input),
                periode=_infer_period_from_filename(path, excel_pointer.get("periode")),
                prodi=prodi,
                jenis_dataset=str(item.get("jenis_dataset") or _dataset_kind(path)) if isinstance(item, dict) else _dataset_kind(path),
            )
            for path, item in zip(pointer_paths, excel_pointer["files"], strict=False)
            if path.exists()
        ]
        if pointer_sources:
            return pointer_sources

    uploaded_bundle = _discover_uploaded_multiyear_bundle()
    if uploaded_bundle:
        return [_excel_source(path, prodi, tahun_input=tahun_input) for path in uploaded_bundle]
    active_excel = pointer.get("active_excel")
    if active_excel:
        paths.append(Path(active_excel))
    if raw_rab_path().exists():
        paths.append(raw_rab_path())
    raw_excel_dir = RAW_DIR / "excel"
    if raw_excel_dir.exists():
        paths.extend(sorted(raw_excel_dir.glob("*.xlsx")))
    unique: list[Path] = []
    seen = set()
    for path in paths:
        if not path.is_absolute():
            path = REPO_ROOT / path
        if path.exists() and path.suffix.lower() in EXCEL_EXTENSIONS:
            resolved = path.resolve()
            if resolved not in seen:
                unique.append(resolved)
                seen.add(resolved)
    return [_excel_source(path, prodi, tahun_input=tahun_input) for path in unique]


def _dataset_kind(path: Path) -> str:
    name = path.name.lower()
    if "nomenklatur" in name:
        return "nomenklatur"
    return "rab"


def _write_parquet(path: Path, df: pd.DataFrame) -> None:
    ensure_parent(path)
    parquet_df = df.copy()
    for column in parquet_df.columns:
        if parquet_df[column].map(lambda value: isinstance(value, (dict, list, tuple))).any():
            parquet_df[column] = parquet_df[column].map(lambda value: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, tuple)) else value)
        elif parquet_df[column].dtype == "object":
            non_null = parquet_df[column].dropna()
            if not non_null.empty and len({type(value) for value in non_null}) > 1:
                parquet_df[column] = parquet_df[column].map(lambda value: None if pd.isna(value) else str(value))
    parquet_df.to_parquet(path, index=False)


def _write_session_and_combined(df: pd.DataFrame, layer: str, filename: str, session_id: str) -> dict[str, str]:
    base = GENERATED_DIR / layer
    session_path = base / session_id / filename
    combined_path = base / filename
    ensure_parent(session_path)
    ensure_parent(combined_path)
    current = df.copy()
    if "dataset_session_id" not in current.columns:
        current["dataset_session_id"] = session_id
    current.to_csv(session_path, index=False)
    current.to_csv(combined_path, index=False)
    parquet_name = f"{Path(filename).stem}.parquet"
    session_parquet = base / session_id / parquet_name
    combined_parquet = base / parquet_name
    _write_parquet(session_parquet, df.assign(dataset_session_id=session_id) if "dataset_session_id" not in df.columns else df)
    _write_parquet(combined_parquet, current)
    return {"csv": str(combined_path), "parquet": str(combined_parquet), "session_csv": str(session_path), "session_parquet": str(session_parquet)}


def _build_rab_reconciliation_report(silver_rab: pd.DataFrame, silver_validation: pd.DataFrame, fact: pd.DataFrame) -> dict[str, object]:
    if silver_rab.empty:
        return {
            "status": "not_available",
            "message": "Tidak ada Silver RAB untuk direkonsiliasi.",
            "final_gold_total": 0,
        }
    main_rab = silver_rab[silver_rab.get("source_role", pd.Series(index=silver_rab.index, dtype=object)).fillna("").eq("main_rab")] if "source_role" in silver_rab.columns else silver_rab.iloc[0:0]
    included = silver_rab[silver_rab.get("include_in_gold", pd.Series(index=silver_rab.index, dtype=bool)).fillna(False).astype(bool)] if "include_in_gold" in silver_rab.columns else silver_rab
    included_main_rab = included[included.get("source_role", pd.Series(index=included.index, dtype=object)).fillna("").eq("main_rab")] if "source_role" in included.columns else included
    orphan = silver_rab[silver_rab.get("row_type", pd.Series(index=silver_rab.index, dtype=object)).fillna("").eq("orphan_leaf_item")] if "row_type" in silver_rab.columns else silver_rab.iloc[0:0]
    detail_support = silver_rab[silver_rab.get("source_role", pd.Series(index=silver_rab.index, dtype=object)).fillna("").eq("detail_support")] if "source_role" in silver_rab.columns else silver_rab.iloc[0:0]
    formula_errors = []
    if not silver_validation.empty and "validation_type" in silver_validation.columns:
        error_rows = silver_validation[silver_validation["validation_type"].eq("FORMULA_ERROR")]
        formula_errors = [
            {
                "cell": row.get("cell"),
                "sheet": row.get("source_sheet"),
                "row": int(row.get("source_row")) if pd.notna(row.get("source_row")) else None,
                "formula": row.get("formula"),
                "error": row.get("formula_error"),
                "severity": row.get("severity") or "high",
            }
            for _, row in error_rows.iterrows()
        ]
    main_rab_final_total = float(pd.to_numeric(included_main_rab.get("jumlah", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not included_main_rab.empty else 0.0
    all_gold_total = float(pd.to_numeric(fact.get("jumlah_weighted_iku", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not fact.empty else 0.0
    return {
        "status": "validated_with_warnings" if len(orphan) or formula_errors else "validated",
        "source_files": sorted(str(value) for value in silver_rab["source_file"].dropna().unique()) if "source_file" in silver_rab.columns else [],
        "main_sheet": "RAB",
        "computed": {
            "main_rab_leaf_total": float(pd.to_numeric(main_rab.get("jumlah", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not main_rab.empty else 0.0,
            "orphan_excluded_total": main_rab_final_total,
            "detail_support_total": float(pd.to_numeric(detail_support.get("jumlah", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()) if not detail_support.empty else 0.0,
            "all_gold_total": all_gold_total,
        },
        "excluded_rows": [
            {
                "sheet": row.get("source_sheet"),
                "row": int(row.get("source_row")) if pd.notna(row.get("source_row")) else None,
                "amount": float(row.get("jumlah") or 0),
                "reason": "orphan_not_in_parent_sum",
                "description": row.get("uraian_detail"),
            }
            for _, row in orphan.iterrows()
        ],
        "formula_errors": formula_errors,
        "warnings": [
            {"reason": "detail_support_sheets_not_included_in_gold_to_prevent_double_count"}
        ] + ([{"reason": "orphan_rows_excluded_from_gold"}] if len(orphan) else []),
        "final_gold_total": main_rab_final_total,
        "all_gold_total": all_gold_total,
    }


def _archive_raw_sources(sources: list[ExcelSource], run_id: str, session_id: str) -> list[dict[str, object]]:
    archive_dir = DATA_DIR / "raw" / "excel_lakehouse" / session_id / run_id
    raw_root = (DATA_DIR / "raw" / "excel_lakehouse").resolve()
    archived = []
    for source in sources:
        source_path = source.path.resolve()
        if source_path.is_relative_to(raw_root):
            target = source_path
            archive_status = "existing_raw_upload"
        else:
            archive_dir.mkdir(parents=True, exist_ok=True)
            target = archive_dir / source.path.name
            archive_status = "copied_to_raw_archive"
            shutil.copy2(source.path, target)
        archived.append(
            {
                "source_path": str(source.path),
                "raw_archive_path": str(target),
                "archive_status": archive_status,
                "filename": target.name,
                "jenis_dataset": source.jenis_dataset,
                "tahun_input": source.tahun_input,
                "periode": source.periode,
                "prodi": source.prodi,
                "size_bytes": target.stat().st_size,
            }
        )
    return archived


def run_excel_lakehouse_pipeline(sources: list[ExcelSource] | None = None) -> dict[str, object]:
    sources = sources if sources is not None else discover_excel_sources()
    session_id = _session_id()
    run_id = str(uuid.uuid4())
    raw_archives = _archive_raw_sources(sources, run_id, session_id)
    bronze_frames: list[pd.DataFrame] = []
    rab_items: list[pd.DataFrame] = []
    rab_hierarchy: list[pd.DataFrame] = []
    rab_validation: list[pd.DataFrame] = []
    nomenklatur_details: list[pd.DataFrame] = []
    nomenklatur_bridge: list[pd.DataFrame] = []
    nomenklatur_warnings: list[pd.DataFrame] = []

    for source in sources:
        bronze_frames.append(extract_excel_cells(source, run_id=run_id))
        if source.jenis_dataset == "nomenklatur":
            detail, bridge, warnings = parse_nomenklatur_workbook(source)
            nomenklatur_details.append(detail)
            nomenklatur_bridge.append(bridge)
            nomenklatur_warnings.append(warnings)
        else:
            items, hierarchy, validation = parse_rab_workbook(source)
            rab_items.append(items)
            rab_hierarchy.append(hierarchy)
            rab_validation.append(validation)

    bronze = pd.concat(bronze_frames, ignore_index=True, sort=False) if bronze_frames else pd.DataFrame()
    silver_rab = pd.concat(rab_items, ignore_index=True, sort=False) if rab_items else pd.DataFrame()
    silver_hierarchy = pd.concat(rab_hierarchy, ignore_index=True, sort=False) if rab_hierarchy else pd.DataFrame()
    silver_validation = pd.concat(rab_validation, ignore_index=True, sort=False) if rab_validation else pd.DataFrame()
    silver_nomenklatur = pd.concat(nomenklatur_details, ignore_index=True, sort=False) if nomenklatur_details else pd.DataFrame()
    bridge_nomenklatur = pd.concat(nomenklatur_bridge, ignore_index=True, sort=False) if nomenklatur_bridge else pd.DataFrame()
    warnings_nomenklatur = pd.concat(nomenklatur_warnings, ignore_index=True, sort=False) if nomenklatur_warnings else pd.DataFrame()
    silver_mapping = build_mapping_table(silver_rab, silver_nomenklatur)
    created_at = utc_now_iso()
    if not silver_rab.empty:
        if "run_id" not in silver_rab.columns:
            silver_rab["run_id"] = run_id
        else:
            silver_rab["run_id"] = silver_rab["run_id"].fillna(run_id)
        if "fakultas" not in silver_rab.columns:
            silver_rab["fakultas"] = active_period_metadata().get("target_fakultas") or "Fakultas Sains"
        if "cluster_kegiatan" not in silver_rab.columns:
            silver_rab["cluster_kegiatan"] = silver_rab.get("kegiatan")
        if "created_at" not in silver_rab.columns:
            silver_rab["created_at"] = created_at
        silver_rab = clean_and_enrich_budget_items(silver_rab, silver_nomenklatur, bridge_nomenklatur)
    fact = build_fact_anggaran(silver_rab)
    silver_rab_rows_classified = silver_rab.copy()
    silver_rab_formula_coverage = (
        silver_validation[silver_validation["validation_type"].eq("FORMULA_COVERAGE")].copy()
        if not silver_validation.empty and "validation_type" in silver_validation.columns
        else pd.DataFrame()
    )
    silver_rab_orphan_items = (
        silver_rab[silver_rab["row_type"].eq("orphan_leaf_item")].copy()
        if not silver_rab.empty and "row_type" in silver_rab.columns
        else pd.DataFrame()
    )
    silver_detail_support_items = (
        silver_rab[silver_rab["source_role"].eq("detail_support")].copy()
        if not silver_rab.empty and "source_role" in silver_rab.columns
        else pd.DataFrame()
    )
    rab_reconciliation_report = _build_rab_reconciliation_report(silver_rab, silver_validation, fact)
    mapped_fact = fact[fact["kode_iku"].notna() & fact["kode_iku"].astype(str).str.strip().ne("")] if not fact.empty else fact
    dashboard_iku = mapped_fact.groupby(["run_id", "tahun", "periode", "prodi", "fakultas", "iku", "kode_iku"], dropna=False)["jumlah_weighted_iku"].sum().reset_index() if not mapped_fact.empty else pd.DataFrame()
    dashboard_mapping = fact.groupby(["run_id", "mapping_status", "data_quality_flag"], dropna=False)["item_id"].nunique().reset_index(name="item_count") if not fact.empty else pd.DataFrame()
    dashboard_detail = fact.copy()
    dashboard_reconciliation = silver_validation.copy()

    outputs = {}
    for layer, filename, df in [
        ("bronze", "bronze_excel_cells.csv", bronze),
        ("silver", "silver_rab_items_flexible.csv", silver_rab),
        ("silver", "silver_rab_rows_classified.csv", silver_rab_rows_classified),
        ("silver", "silver_rab_formula_coverage.csv", silver_rab_formula_coverage),
        ("silver", "silver_rab_orphan_items.csv", silver_rab_orphan_items),
        ("silver", "silver_detail_support_items.csv", silver_detail_support_items),
        ("silver", "silver_rab_hierarchy.csv", silver_hierarchy),
        ("silver", "silver_mapping.csv", silver_mapping),
        ("silver", "silver_validation.csv", silver_validation),
        ("silver", "silver_nomenklatur_detail.csv", silver_nomenklatur),
        ("silver", "silver_bridge_detail_iku.csv", bridge_nomenklatur),
        ("silver", "silver_nomenklatur_warnings.csv", warnings_nomenklatur),
        ("gold", "fact_anggaran.csv", fact),
        ("gold", "vw_dashboard_iku_anggaran.csv", dashboard_iku),
        ("gold", "vw_dashboard_mapping_quality.csv", dashboard_mapping),
        ("gold", "vw_dashboard_reconciliation.csv", dashboard_reconciliation),
        ("gold", "vw_dashboard_detail_item.csv", dashboard_detail),
    ]:
        outputs[filename] = _write_session_and_combined(df, layer, filename, session_id)

    metadata = {
        "run_id": run_id,
        "dataset_session_id": session_id,
        "source_files": [str(source.path) for source in sources],
        "raw_archives": raw_archives,
        "bronze_cells": int(len(bronze)),
        "silver_rab_items": int(len(silver_rab)),
        "silver_nomenklatur_detail": int(len(silver_nomenklatur)),
        "fact_anggaran_rows": int(len(fact)),
        "rab_reconciliation_status": rab_reconciliation_report.get("status"),
        "rab_reconciliation_final_gold_total": rab_reconciliation_report.get("final_gold_total"),
        "outputs": outputs,
    }
    write_json(GENERATED_DIR / "excel_lakehouse_metadata.json", metadata)
    write_json(OUTPUTS_DIR / "reports" / "rab_reconciliation_report.json", rab_reconciliation_report)
    return metadata


def main() -> None:
    print(run_excel_lakehouse_pipeline())


if __name__ == "__main__":
    main()
