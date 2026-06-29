from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

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
