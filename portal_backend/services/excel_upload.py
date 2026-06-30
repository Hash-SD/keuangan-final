from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4
import re

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .files import relative_path, write_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso


ACTIVE_EXCEL_DATASET_PATH = OUTPUTS_DIR / "reports" / "active_excel_lakehouse_dataset.json"
EXCEL_DATASET_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "excel_dataset_registry.json"


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
    dataset_id = f"excel-{utc_now_iso().replace(':', '').replace('-', '').split('.')[0]}-{uuid4().hex[:6]}"
    target_dir = DATA_DIR / "raw" / "excel_lakehouse" / _safe(tahun_input, "unknown") / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for upload in uploads:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
            raise ValueError("Semua file harus berupa workbook Excel .xlsx/.xlsm/.xltx/.xltm.")
        filename = secure_filename(upload.filename or f"workbook{suffix}")
        target = (target_dir / filename).resolve()
        if target_dir.resolve() not in target.parents:
            raise ValueError("Path upload Excel tidak valid.")
        upload.save(target)
        saved.append(
            {
                "filename": filename,
                "path": relative_path(target),
                "size_bytes": target.stat().st_size,
                "jenis_dataset": _kind(filename, jenis_dataset),
            }
        )
    scope = _upload_scope(saved, tahun_input or None)

    dataset = {
        "dataset_id": dataset_id,
        "status": "committed",
        "excel_only": True,
        "tahun_input": tahun_input or None,
        "periode": periode,
        "prodi": prodi,
        "fakultas": fakultas,
        "jenis_dataset": jenis_dataset,
        "catatan": catatan,
        **scope,
        "files": saved,
        "created_at": utc_now_iso(),
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
