"""Build a read-only, timestamped Bab IV evidence packet for sections 4.1-4.3."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
OUT_BASE = ROOT / "outputs" / "bab4_evidence_final"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = sorted({k for row in rows for k in row}) or ["status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)


def read_json(path: Path, default: object) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def classify_sheet(title: str) -> tuple[str, str]:
    low = title.lower()
    if "nomen" in low or "refer" in low:
        return "reference", "Nama sheet menunjukkan referensi/nomenklatur."
    if "rab" in low or "anggaran" in low:
        return "main_rab", "Nama sheet menunjukkan RAB/anggaran."
    if "rekon" in low:
        return "reconciliation", "Nama sheet menunjukkan rekonsiliasi."
    if "detail" in low or "rinc" in low:
        return "detail_support", "Nama sheet menunjukkan rincian pendukung."
    return "unknown", "Tidak ada penanda nama yang cukup untuk klasifikasi otomatis."


def chart(frame: pd.DataFrame, x: str, y: str, path: Path, title: str, ylabel: str, run_id: str) -> None:
    if frame.empty:
        return
    frame.to_csv(path.with_suffix(".csv"), index=False, encoding="utf-8-sig")
    plt.figure(figsize=(10, 5))
    plt.bar(frame[x].astype(str), pd.to_numeric(frame[y], errors="coerce").fillna(0))
    plt.title(title); plt.xlabel(x); plt.ylabel(ylabel); plt.xticks(rotation=35, ha="right")
    plt.figtext(0.01, 0.01, f"Sumber: artefak canonical run {run_id}", fontsize=7)
    plt.tight_layout(); plt.savefig(path, dpi=220); plt.close()


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("audit_%Y%m%dT%H%M%SZ")
    out = OUT_BASE / stamp
    for folder in ("00_manifest", "01_perancangan/411_analisis_sumber", "01_perancangan/412_arsitektur_dan_aturan", "01_perancangan/413_model_gold_dan_lineage", "02_implementasi/421_lingkungan_dan_orkestrasi", "02_implementasi/422_bronze_dan_silver", "02_implementasi/423_gold_dan_dashboard", "03_pengujian/431_kualitas_dan_rekonsiliasi", "03_pengujian/432_kinerja_dan_dashboard", "03_pengujian/433_uat_dan_pembahasan", "tables", "figures", "screenshots", "final_validation"):
        (out / folder).mkdir(parents=True, exist_ok=True)

    active = read_json(ROOT / "outputs/reports/active_excel_lakehouse_dataset.json", {})
    gold_run = read_json(ROOT / "outputs/reports/active_gold_run.json", {})
    storage = read_json(ROOT / "outputs/reports/storage_manifest.json", {})
    pipeline_id = str(gold_run.get("pipeline_run_id") or storage.get("pipeline_run_id") or "")
    dataset_id = str(gold_run.get("dataset_session_id") or storage.get("dataset_session_id") or active.get("dataset_session_id") or "")
    run_report = read_json(ROOT / "outputs/reports/pipeline_runs" / f"{pipeline_id}.json", {}) if pipeline_id else {}
    airflow_id = str(run_report.get("airflow_dag_run_id") or gold_run.get("airflow_dag_run_id") or "")

    source_rows = []
    sheet_rows = []
    formula_rows = []
    merged_rows = []
    files = active.get("files", []) if isinstance(active, dict) else []
    for item in files:
        path = Path(item.get("path", ""))
        if not path.exists():
            continue
        wb = load_workbook(path, read_only=False, data_only=False)
        formulas = 0; formula_errors = 0; merged = 0; cells = 0
        for ws in wb.worksheets:
            nonempty = 0; ws_formula = 0; ws_errors = 0
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None: nonempty += 1; cells += 1
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        ws_formula += 1; formulas += 1
                        if any(token in cell.value.upper() for token in ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?")):
                            ws_errors += 1; formula_errors += 1
            role, reason = classify_sheet(ws.title)
            sheet_rows.append({"dataset_session_id": dataset_id, "source_file": path.name, "source_sheet": ws.title, "max_row": ws.max_row, "max_column": ws.max_column, "nonempty_cells": nonempty, "formula_count": ws_formula, "formula_error_count": ws_errors, "merged_range_count": len(ws.merged_cells.ranges), "sheet_visibility": ws.sheet_state, "sheet_role": role, "classification_reason": reason})
            for rng in ws.merged_cells.ranges:
                merged_rows.append({"source_file": path.name, "source_sheet": ws.title, "range": str(rng)})
            if ws_formula:
                formula_rows.append({"source_file": path.name, "source_sheet": ws.title, "formula_count": ws_formula, "formula_error_count": ws_errors})
        wb.close()
        source_rows.append({"dataset_session_id": dataset_id, "source_file": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path), "sheet_count": len(wb.sheetnames) if False else sum(1 for r in sheet_rows if r["source_file"] == path.name), "filled_cells": cells, "formula_count": formulas, "formula_error_count": formula_errors, "merged_range_count": sum(1 for r in merged_rows if r["source_file"] == path.name), "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(), "openable": True, "jenis_dataset": item.get("jenis_dataset")})

    base411 = out / "01_perancangan/411_analisis_sumber"
    write_csv(base411 / "workbook_inventory.csv", source_rows)
    write_csv(base411 / "sheet_inventory.csv", sheet_rows)
    write_csv(base411 / "formula_error_detail.csv", [r for r in formula_rows if r["formula_error_count"]])
    write_csv(base411 / "merged_range_summary.csv", merged_rows)
    roles = pd.DataFrame(sheet_rows).groupby("sheet_role", dropna=False).size().reset_index(name="sheet_count").to_dict("records") if sheet_rows else []
    write_csv(base411 / "sheet_role_summary.csv", roles)
    write_csv(base411 / "source_structure_profile.csv", [{"metric": "workbooks", "value": len(source_rows)}, {"metric": "sheets", "value": len(sheet_rows)}, {"metric": "formula_cells", "value": sum(r["formula_count"] for r in source_rows)}, {"metric": "formula_error_cells", "value": sum(r["formula_error_count"] for r in source_rows)}, {"metric": "merged_ranges", "value": len(merged_rows)}])
    write_csv(base411 / "source_problem_summary.csv", [{"problem": "formula_error", "count": sum(r["formula_error_count"] for r in source_rows), "status": "observed"}, {"problem": "unknown_sheet_role", "count": sum(r["sheet_role"] == "unknown" for r in sheet_rows), "status": "requires_review"}])
    write_csv(base411 / "system_requirement_matrix.csv", [{"requirement": x, "evidence_basis": "workbook/sheet profiling and pipeline implementation", "status": "derived"} for x in ("multi-workbook integration", "cell-level extraction", "sheet and row classification", "formula validation", "lineage", "reconciliation", "double-count prevention", "dashboard validation", "UAT")])
    chart(pd.DataFrame(source_rows), "source_file", "filled_cells", out / "figures/fig_411_cells_per_workbook.png", "Sel Terisi per Workbook", "Jumlah sel", pipeline_id)
    chart(pd.DataFrame(source_rows), "source_file", "formula_count", out / "figures/fig_411_formula_per_workbook.png", "Formula per Workbook", "Jumlah formula", pipeline_id)

    base422 = out / "02_implementasi/422_bronze_dan_silver"
    session_root = ROOT / "data/generated"
    bronze = pd.read_csv(session_root / "bronze" / f"{dataset_id}" / pipeline_id / "bronze_excel_cells.csv") if pipeline_id and (session_root / "bronze" / dataset_id / pipeline_id / "bronze_excel_cells.csv").exists() else pd.read_csv(session_root / "bronze/bronze_excel_cells.csv")
    silver = pd.read_csv(session_root / "silver" / f"{dataset_id}" / pipeline_id / "silver_rab_items_flexible.csv") if pipeline_id and (session_root / "silver" / dataset_id / pipeline_id / "silver_rab_items_flexible.csv").exists() else pd.read_csv(session_root / "silver/silver_rab_items_flexible.csv")
    gold = pd.read_csv(session_root / "gold" / f"{dataset_id}" / pipeline_id / "fact_anggaran.csv") if pipeline_id and (session_root / "gold" / dataset_id / pipeline_id / "fact_anggaran.csv").exists() else pd.read_csv(session_root / "gold/fact_anggaran.csv")
    write_csv(base422 / "bronze_summary_by_file.csv", [{"source_file": k, "cell_count": int(v)} for k, v in bronze.groupby("source_file").size().items()])
    write_csv(base422 / "bronze_summary_by_sheet.csv", [{"source_sheet": k, "cell_count": int(v)} for k, v in bronze.groupby("source_sheet").size().items()] if "source_sheet" in bronze else [])
    write_csv(base422 / "bronze_schema_dictionary.csv", [{"column": c, "dtype": str(t), "nullable": bool(bronze[c].isna().any())} for c, t in bronze.dtypes.items()])
    write_csv(base422 / "silver_row_type_summary.csv", [{"row_type": str(k), "row_count": int(v)} for k, v in silver.groupby("row_type", dropna=False).size().items()] if "row_type" in silver else [])
    write_csv(base422 / "silver_source_role_summary.csv", [{"source_role": str(k), "row_count": int(v)} for k, v in silver.groupby("source_role", dropna=False).size().items()] if "source_role" in silver else [])
    write_csv(base422 / "silver_schema_dictionary.csv", [{"column": c, "dtype": str(t), "nullable": bool(silver[c].isna().any())} for c, t in silver.dtypes.items()])
    for name in ("silver_rab_formula_coverage.csv", "silver_rab_orphan_items.csv", "silver_validation.csv", "silver_mapping.csv"):
        src = ROOT / "data/generated/silver" / name
        if src.exists(): shutil.copy2(src, base422 / name)
    write_csv(out / "01_perancangan/412_arsitektur_dan_aturan/business_rule_inventory.csv", [{"rule": r, "source": s, "status": "observed_in_code_or_artifact"} for r, s in (("Bronze grain: one cell per workbook/run", "src/excel_ingestion/excel_cell_extractor.py"), ("Silver grain: candidate budget item", "src/transformations/excel_lakehouse_pipeline.py"), ("Gold grain: item x IKU allocation", "src/gold/fact_anggaran.py"), ("weighted amount conservation", "outputs/reports/pipeline_count_validation.json"), ("subtotal/total exclusion", "src/gold/fact_anggaran.py"), ("detail support double-count prevention", "src/transformations/excel_lakehouse_pipeline.py"))])
    write_csv(out / "01_perancangan/412_arsitektur_dan_aturan/grain_definition.csv", [{"layer": "Bronze", "grain": "one cell per workbook and run"}, {"layer": "Silver", "grain": "one candidate budget item"}, {"layer": "Gold", "grain": "one budget item per IKU allocation"}])
    write_csv(out / "01_perancangan/413_model_gold_dan_lineage/fact_schema_dictionary.csv", [{"column": c, "dtype": str(t), "nullable": bool(gold[c].isna().any())} for c, t in gold.dtypes.items()])
    write_json(out / "01_perancangan/413_model_gold_dan_lineage/dimensional_model_status.json", {"status": "CONCEPTUAL_MODEL_ONLY", "physical_fact": "gold.fact_anggaran", "reason": "No complete physical dimension-table evidence was found in the canonical packet."})
    lineage_cols = [c for c in ("dataset_session_id", "pipeline_run_id", "item_id", "source_file", "source_sheet", "source_row", "cell_address", "created_at") if c in gold.columns]
    write_csv(out / "01_perancangan/413_model_gold_dan_lineage/lineage_completeness.csv", [{"column": c, "non_null": int(gold[c].notna().sum()), "total": len(gold), "completeness_percent": float(gold[c].notna().mean() * 100)} for c in lineage_cols])
    write_csv(out / "01_perancangan/413_model_gold_dan_lineage/lineage_samples.csv", gold[lineage_cols].head(5).to_dict("records") if lineage_cols else [])

    base431 = out / "03_pengujian/431_kualitas_dan_rekonsiliasi"
    amount_col = "jumlah_weighted_iku" if "jumlah_weighted_iku" in gold else "jumlah"
    summary = [{"dataset_session_id": dataset_id, "pipeline_run_id": pipeline_id, "bronze_rows": len(bronze), "silver_rows": len(silver), "gold_rows": len(gold), "unique_items": int(gold["item_id"].nunique()) if "item_id" in gold else None, "weighted_total": float(pd.to_numeric(gold[amount_col], errors="coerce").sum()), "duplicate_rows": int(gold.duplicated().sum()), "status": "VALIDATED" if gold.duplicated().sum() == 0 else "WARNING"}]
    write_csv(base431 / "layer_count_validation.csv", summary)
    if "item_id" in gold and "allocation_weight" in gold:
        alloc = gold.groupby("item_id", dropna=False).agg(allocation_weight_sum=("allocation_weight", "sum"), weighted_total=(amount_col, "sum"), source_amount=("jumlah", "first") if "jumlah" in gold else (amount_col, "first")).reset_index()
        alloc["allocation_valid"] = (alloc["allocation_weight_sum"] - 1).abs() <= 0.0001
        write_csv(base431 / "iku_allocation_validation.csv", alloc.to_dict("records"))
    write_csv(base431 / "reconciliation_summary.csv", [{"scope": "canonical Gold", "gold_weighted_total": summary[0]["weighted_total"], "status": "VALIDATED_WITH_LIMITATIONS", "note": "Source-control total and dashboard refresh timestamps require separate matched-run evidence."}])

    base433 = out / "03_pengujian/433_uat_dan_pembahasan"
    uat = read_json(ROOT / "outputs/reports/uat_local_submissions.json", {})
    write_json(base433 / "uat_source_snapshot.json", uat)
    write_csv(base433 / "uat_respondent.csv", [{"respondent_id": "R1-anonymized", "respondent_count": 1, "source": "outputs/reports/uat_local_submissions.json"}] if uat else [])
    submission_count = len(uat.get("submissions", uat.get("items", []))) if isinstance(uat, dict) else 0
    score_answers = sum(len(item.get("scores", [])) for item in uat.get("items", [])) if isinstance(uat, dict) else 0
    write_csv(base433 / "uat_submission_summary.csv", [{"submission_count": submission_count, "score_answers": score_answers, "status": "OBSERVED" if uat else "NOT_FOUND"}])

    write_json(out / "00_manifest/canonical_run_manifest.json", {"status": "VALID" if dataset_id and pipeline_id and storage.get("dataset_session_id") == dataset_id and storage.get("pipeline_run_id") == pipeline_id else "NOT_READY", "dataset_session_id": dataset_id, "pipeline_run_id": pipeline_id, "airflow_dag_run_id": airflow_id or None, "source_file_count": len(source_rows), "source_files": source_rows, "run_report_present": bool(run_report), "active_pointer_dataset_id": active.get("dataset_session_id"), "generated_at": now()})
    write_csv(out / "00_manifest/canonical_run_manifest.csv", [{"dataset_session_id": dataset_id, "pipeline_run_id": pipeline_id, "airflow_dag_run_id": airflow_id or None, "source_file_count": len(source_rows), "status": "VALID" if dataset_id and pipeline_id else "NOT_READY"}])
    write_json(out / "00_manifest/reproducibility.json", {"git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(), "branch": subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True).stdout.strip(), "generated_at": now(), "read_only": True})
    write_json(out / "final_validation/section_readiness.json", {"4.1.1": "READY" if source_rows and sheet_rows else "NOT_READY", "4.1.2": "READY_WITH_LIMITATIONS", "4.1.3": "READY_WITH_LIMITATIONS" if lineage_cols else "NOT_READY", "4.2.1": "READY_WITH_LIMITATIONS" if pipeline_id else "NOT_READY", "4.2.2": "READY" if len(bronze) and len(silver) else "NOT_READY", "4.2.3": "READY_WITH_LIMITATIONS" if len(gold) else "NOT_READY", "4.3.1": summary[0]["status"], "4.3.2": "NOT_READY", "4.3.3": "READY_WITH_LIMITATIONS" if uat else "NOT_READY", "overall_decision": "NOT_READY_FOR_FINAL_WRITING", "limitations": ["Airflow DAG run ID belum terikat pada canonical run.", "Metadata generated root masih menunjuk run lama.", "Bukti lima run T0-T1-T2 belum lengkap.", "Screenshot aktual harus diambil user dari layar sistem."]})
    (out / "final_validation/section_readiness.md").write_text("# Readiness Bab IV 4.1–4.3\n\nKeputusan: **NOT_READY_FOR_FINAL_WRITING**.\n\nBukti hanya berasal dari artefak dan runtime yang dapat ditelusuri; nilai kosong tidak diisi asumsi.\n", encoding="utf-8")
    (out / "screenshots/README.md").write_text("# Instruksi Screenshot untuk User\n\nAmbil screenshot aktual berikut setelah membuka sistem:\n\n- Docker Compose: daftar service dan health status.\n- Airflow Grid: DAG run canonical dan status task.\n- Airflow Graph: dependensi task.\n- Log task pipeline: extraction, Bronze, Silver, Gold, PostgreSQL, Superset.\n- MinIO: object path canonical Bronze/Silver/Gold.\n- PostgreSQL/Trino: hasil query count dan weighted total.\n- Superset: dashboard, filter tahun/IKU/kegiatan/akun, KPI, grafik, detail item, dan lineage.\n\nJangan menampilkan password, token, cookie, access key, atau secret key. Simpan dengan nama file yang sama seperti daftar di atas dan cantumkan timestamp serta canonical run ID.\n", encoding="utf-8")
    artifacts = []
    for p in out.rglob("*"):
        if p.is_file() and p.name != "artifact_manifest.csv": artifacts.append({"path": p.relative_to(out).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256(p)})
    write_csv(out / "00_manifest/artifact_manifest.csv", artifacts, ["path", "size_bytes", "sha256"])
    print(json.dumps({"output": str(out), "dataset_session_id": dataset_id, "pipeline_run_id": pipeline_id, "airflow_dag_run_id": airflow_id or None, "decision": "NOT_READY_FOR_FINAL_WRITING"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
