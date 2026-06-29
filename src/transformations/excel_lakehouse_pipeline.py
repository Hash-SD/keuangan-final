from __future__ import annotations

import os
import sys
import uuid
import json
import shutil
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import DATA_DIR, GENERATED_DIR, RAW_DIR, ensure_parent
from src.common.runtime_paths import active_dataset_pointer, active_period_metadata, raw_rab_path
from src.common.time_utils import utc_now_iso
from src.excel_ingestion.excel_cell_extractor import ExcelSource, extract_excel_cells
from src.gold.fact_anggaran import build_fact_anggaran
from src.mapping.flexible_mapping import build_mapping_table
from src.parser_flexible.nomenklatur_parser import parse_nomenklatur_workbook
from src.parser_flexible.rab_parser import parse_rab_workbook


def _session_id() -> str:
    pointer = active_dataset_pointer() or {}
    return Path(str(pointer.get("session_id") or "dummy")).name or "dummy"


def _split_env_paths(value: str | None) -> list[Path]:
    if not value:
        return []
    return [Path(item.strip()) for item in value.split(";") if item.strip()]


def discover_excel_sources() -> list[ExcelSource]:
    pointer = active_dataset_pointer() or {}
    excel_pointer_path = Path(__file__).resolve().parents[2] / "outputs" / "reports" / "active_excel_lakehouse_dataset.json"
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
    if not env_paths and isinstance(excel_pointer.get("files"), list):
        paths.extend(Path(str(item.get("path") or item)) for item in excel_pointer["files"])
        pointer_paths = [path if path.is_absolute() else Path(__file__).resolve().parents[2] / path for path in paths]
        if pointer_paths:
            return [
                ExcelSource(
                    path=path.resolve(),
                    tahun_input=tahun_input,
                    periode=excel_pointer.get("periode"),
                    prodi=prodi,
                    jenis_dataset=str(item.get("jenis_dataset") or _dataset_kind(path)) if isinstance(item, dict) else _dataset_kind(path),
                )
                for path, item in zip(pointer_paths, excel_pointer["files"], strict=False)
                if path.exists()
            ]
    if env_paths:
        return [
            ExcelSource(path=path.resolve() if path.is_absolute() else (Path(__file__).resolve().parents[2] / path).resolve(), tahun_input=tahun_input, prodi=prodi, jenis_dataset=_dataset_kind(path))
            for path in paths
            if (path if path.is_absolute() else Path(__file__).resolve().parents[2] / path).exists()
        ]
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
            path = Path(__file__).resolve().parents[2] / path
        if path.exists() and path.suffix.lower() in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
            resolved = path.resolve()
            if resolved not in seen:
                unique.append(resolved)
                seen.add(resolved)
    return [ExcelSource(path=path, tahun_input=tahun_input, prodi=prodi, jenis_dataset=_dataset_kind(path)) for path in unique]


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
    if combined_path.exists():
        existing = pd.read_csv(combined_path)
        if "dataset_session_id" in existing.columns:
            existing = existing[existing["dataset_session_id"].fillna("").astype(str) != session_id]
            current = pd.concat([existing, current], ignore_index=True, sort=False)
    current.to_csv(combined_path, index=False)
    parquet_name = f"{Path(filename).stem}.parquet"
    session_parquet = base / session_id / parquet_name
    combined_parquet = base / parquet_name
    _write_parquet(session_parquet, df.assign(dataset_session_id=session_id) if "dataset_session_id" not in df.columns else df)
    _write_parquet(combined_parquet, current)
    return {"csv": str(combined_path), "parquet": str(combined_parquet), "session_csv": str(session_path), "session_parquet": str(session_parquet)}


def _archive_raw_sources(sources: list[ExcelSource], run_id: str, session_id: str) -> list[dict[str, object]]:
    archive_dir = DATA_DIR / "raw" / "excel_lakehouse" / session_id / run_id
    archive_dir.mkdir(parents=True, exist_ok=True)
    archived = []
    for source in sources:
        target = archive_dir / source.path.name
        if source.path.resolve() != target.resolve():
            shutil.copy2(source.path, target)
        archived.append(
            {
                "source_path": str(source.path),
                "raw_archive_path": str(target),
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
    fact = build_fact_anggaran(silver_rab)
    dashboard_iku = fact.groupby(["run_id", "tahun", "periode", "prodi", "fakultas", "iku"], dropna=False)["jumlah_weighted_iku"].sum().reset_index() if not fact.empty else pd.DataFrame()
    dashboard_mapping = fact.groupby(["run_id", "mapping_status", "data_quality_flag"], dropna=False)["item_id"].nunique().reset_index(name="item_count") if not fact.empty else pd.DataFrame()
    dashboard_detail = fact.copy()
    dashboard_reconciliation = silver_validation.copy()

    outputs = {}
    for layer, filename, df in [
        ("bronze", "bronze_excel_cells.csv", bronze),
        ("silver", "silver_rab_items_flexible.csv", silver_rab),
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
        "outputs": outputs,
    }
    write_json(GENERATED_DIR / "excel_lakehouse_metadata.json", metadata)
    return metadata


def main() -> None:
    print(run_excel_lakehouse_pipeline())


if __name__ == "__main__":
    main()
