from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4
import hashlib
import re
import shutil

from openpyxl import load_workbook

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .files import read_json, relative_path, write_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso


ACTIVE_EXCEL_DATASET_PATH = OUTPUTS_DIR / "reports" / "active_excel_lakehouse_dataset.json"
EXCEL_DATASET_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "excel_dataset_registry.json"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _safe(value: object, fallback: str = "unknown") -> str:
    return secure_filename(str(value or fallback).replace("/", "-")) or fallback


def _kind(filename: str, explicit: str | None = None) -> str:
    if explicit in {"rab", "rpd", "iku", "nomenklatur"}:
        return explicit
    return "nomenklatur" if "nomenklatur" in filename.lower() else "rab"


def _detect_year(filename: str, fallback: str | None) -> str | None:
    match = re.search(r"\b(20\d{2})\b", filename)
    return match.group(1) if match else fallback


def _upload_scope(saved: list[dict[str, Any]], tahun_input: str | None) -> dict[str, Any]:
    years = sorted({year for item in saved if (year := _detect_year(str(item["filename"]), tahun_input))})
    kinds = {str(item.get("jenis_dataset") or "") for item in saved}
    has_nomenklatur = "nomenklatur" in kinds
    has_2025_like = any("2025" in str(item["filename"]) or _detect_year(str(item["filename"]), tahun_input) == "2025" for item in saved)
    warnings: list[str] = []
    if not has_nomenklatur:
        warnings.append("Nomenklatur belum diunggah; mapping IKU dapat berstatus perlu review.")
    if len(years) > 1 and not has_2025_like:
        warnings.append("Upload multi-tahun sebaiknya menyertakan workbook 2025-like sebagai acuan format.")
    if not years:
        warnings.append("Tahun tidak terdeteksi dari metadata atau nama file.")
    return {
        "upload_scope": "multi_year_bundle" if len(years) > 1 else "single_year",
        "detected_years": years,
        "has_nomenklatur": has_nomenklatur,
        "has_2025_like_template": has_2025_like,
        "warnings": warnings,
    }


def commit_excel_lakehouse_dataset(form: Any, files: Any) -> dict[str, Any]:
    upload_started_at = utc_now_iso()
    uploads: list[FileStorage] = []
    for key in ["file_excel", "file_excel[]", "excel", "files", "file"]:
        uploads.extend([item for item in files.getlist(key) if item and item.filename])
    if not uploads:
        raise ValueError("Minimal satu file Excel wajib diunggah.")

    tahun_input = str(form.get("tahun_input") or form.get("tahun_anggaran") or "").strip()
    prodi = str(form.get("prodi") or "Sains Data").strip()
    fakultas = str(form.get("fakultas") or "Fakultas Sains").strip()
    periode = str(form.get("periode") or "").strip() or None
    jenis_dataset = str(form.get("jenis_dataset") or "").strip().lower() or None
    catatan = str(form.get("catatan") or "").strip() or None
    append_to_active = str(form.get("append_to_active") or "").strip().lower() == "true"
    dashboard_mode = str(form.get("dashboard_mode") or "update").strip().lower()
    if dashboard_mode not in {"update", "new"}:
        dashboard_mode = "update"
    dataset_id = f"excel-{utc_now_iso().replace(':', '').replace('-', '').split('.')[0]}-{uuid4().hex[:6]}"
    if len(uploads) > 20:
        raise ValueError("Jumlah workbook melebihi batas 20 file per dataset.")
    staging_dir = DATA_DIR / "uploads" / "staging" / dataset_id
    target_dir = DATA_DIR / "raw" / "excel_lakehouse" / _safe(tahun_input, "unknown") / dataset_id
    saved: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    try:
        staging_dir.mkdir(parents=True, exist_ok=False)
        for upload in uploads:
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
                raise ValueError("Semua file harus berupa workbook Excel .xlsx/.xlsm/.xltx/.xltm.")
            filename = secure_filename(upload.filename or f"workbook{suffix}")
            if not filename or filename in seen_names:
                raise ValueError("Nama workbook duplikat atau tidak aman.")
            seen_names.add(filename)
            target = (staging_dir / filename).resolve()
            if staging_dir.resolve() not in target.parents:
                raise ValueError("Path upload Excel tidak valid.")
            upload.save(target)
            size_bytes = target.stat().st_size
            if size_bytes <= 0:
                raise ValueError("Workbook tidak boleh kosong.")
            if size_bytes > MAX_UPLOAD_BYTES:
                raise ValueError("Ukuran workbook melebihi batas upload.")
            try:
                workbook = load_workbook(target, read_only=True, data_only=False)
                sheet_count = len(workbook.sheetnames)
                workbook.close()
            except Exception as exc:
                raise ValueError(f"Workbook tidak dapat dibuka atau rusak: {filename}") from exc
            saved.append(
                {
                    "filename": filename,
                    "path": None,
                    "size_bytes": size_bytes,
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "workbook_openable": True,
                    "sheet_count": sheet_count,
                    "jenis_dataset": _kind(filename, jenis_dataset),
                }
            )
        active = read_json(ACTIVE_EXCEL_DATASET_PATH) if append_to_active else None
        active_files = active.get("files", []) if isinstance(active, dict) and active.get("status") == "committed" else []
        active_kinds = {str(item.get("jenis_dataset") or "") for item in active_files if isinstance(item, dict)}
        incoming_kinds = {str(item.get("jenis_dataset") or "") for item in saved}
        complementary_bundle = bool(active_files) and ((incoming_kinds == {"nomenklatur"} and "rab" in active_kinds) or (incoming_kinds == {"rab"} and "nomenklatur" in active_kinds))
        if complementary_bundle:
            first_path = Path(str(active_files[0].get("path") or ""))
            existing_dir = first_path.parent if first_path.is_absolute() else (ROOT_DIR / first_path).parent
            if not existing_dir.exists():
                raise ValueError("Dataset aktif tidak dapat ditambah karena direktori sumber tidak tersedia.")
            for item in saved:
                if (existing_dir / str(item["filename"])).exists():
                    raise ValueError("Nama workbook Nomenklatur sudah ada pada dataset aktif.")
            for item in saved:
                shutil.move(str(staging_dir / str(item["filename"])), str(existing_dir / str(item["filename"])))
            staging_dir.rmdir()
            target_dir = existing_dir
            dataset_id = str(active.get("dataset_session_id") or active.get("dataset_id"))
            saved = [*active_files, *saved]
        else:
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            staging_dir.replace(target_dir)
        for item in saved:
            if not item.get("path"):
                item["path"] = relative_path(target_dir / str(item["filename"]))
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    scope = _upload_scope(saved, tahun_input or None)

    upload_committed_at = utc_now_iso()
    dataset = {
        "dataset_id": dataset_id,
        "dataset_session_id": dataset_id,
        "status": "committed",
        "upload_state": "COMMITTED",
        "validation_status": "VALIDATED",
        "excel_only": True,
        "tahun_input": tahun_input or None,
        "periode": periode,
        "prodi": prodi,
        "fakultas": fakultas,
        "jenis_dataset": jenis_dataset,
        "catatan": catatan,
        "dashboard_mode": dashboard_mode,
        **scope,
        "files": saved,
        "upload_started_at": upload_started_at,
        "upload_committed_at": upload_committed_at,
        "created_at": upload_committed_at,
    }
    write_json(ACTIVE_EXCEL_DATASET_PATH, dataset)
    registry = {"active_dataset_id": dataset_id, "updated_at": utc_now_iso(), "datasets": [dataset]}
    if EXCEL_DATASET_REGISTRY_PATH.exists():
        try:
            import json

            previous = json.loads(EXCEL_DATASET_REGISTRY_PATH.read_text(encoding="utf-8"))
            registry["datasets"].extend([item for item in previous.get("datasets", []) if item.get("dataset_id") != dataset_id])
        except Exception:
            pass
    write_json(EXCEL_DATASET_REGISTRY_PATH, registry)
    return dataset
