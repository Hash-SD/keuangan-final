from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from openpyxl import load_workbook
from pypdf import PdfReader
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .files import relative_path, write_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR
from .runtime_context import normalize_context, read_active_context, write_active_context
from src.common.time_utils import utc_now_iso


STAGING_ROOT = DATA_DIR / "uploads" / "staging"
ACTIVE_SESSION_PATH = OUTPUTS_DIR / "reports" / "active_upload_session.json"
UPLOAD_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "upload_registry.json"
DATASET_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "dataset_registry.json"
AVAILABLE_PERIODS_PATH = OUTPUTS_DIR / "reports" / "available_periods.json"
LATEST_UPLOAD_METADATA_PATH = OUTPUTS_DIR / "reports" / "latest_upload_metadata.json"
ACTIVE_DATASET_POINTER_PATH = OUTPUTS_DIR / "reports" / "active_dataset_pointer.json"
SYSTEM_TRUTH_STATUS_PATH = OUTPUTS_DIR / "reports" / "system_truth_status.json"
SESSION_STATUS_FILENAME = "session_status.json"
VALIDATION_PREVIEW_FILENAME = "validation_preview.json"

CSV_REQUIRED_COLUMNS = {
    "transaction_id",
    "nim_dummy",
    "tanggal",
    "semester",
    "tahun_akademik",
    "jenis_biaya",
    "prodi",
    "fakultas",
    "golongan_ukt",
    "nominal_tagihan",
    "nominal_bayar",
    "metode_bayar",
    "status_bayar",
}

RAB_REQUIRED_COLUMNS = {
    "kode_akun",
    "nama_kegiatan",
    "kategori",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "Mei",
    "Jun",
    "Jul",
    "Agu",
    "Sep",
    "Okt",
    "Nov",
    "Des",
    "total_pagu",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _safe_period(value: str | None, fallback: str = "unknown") -> str:
    text = str(value or fallback).strip().replace("/", "-")
    return secure_filename(text) or fallback


def _new_session_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return f"upload-{stamp}-{uuid4().hex[:6]}"


def _empty_session() -> dict[str, Any]:
    context = read_active_context()
    return {
        "session_id": _new_session_id(),
        "status": "draft",
        "context": context,
        "files": {"pdf": None, "csv": [], "excel": None},
        "created_at": utc_now_iso(),
        "updated_at": utc_now_iso(),
        "commit_status": "not_committed",
    }


def _session_dir(session: dict[str, Any]) -> Path:
    return STAGING_ROOT / session["session_id"]


def _session_status_path(session: dict[str, Any]) -> Path:
    return _session_dir(session) / SESSION_STATUS_FILENAME


def _validation_preview_path(session: dict[str, Any]) -> Path:
    return _session_dir(session) / VALIDATION_PREVIEW_FILENAME


def _session_record(session: dict[str, Any]) -> dict[str, Any]:
    record = {key: value for key, value in session.items() if key not in {"readiness", "validation_errors", "raw_layer", "pipeline_state", "message", "dataset_pointer"}}
    files = record.setdefault("files", {"pdf": None, "csv": [], "excel": None})
    if isinstance(files.get("pdf"), dict) and "items" in files["pdf"] and files["pdf"].get("available") is False:
        files["pdf"] = None
    if isinstance(files.get("excel"), dict) and "items" in files["excel"] and files["excel"].get("available") is False:
        files["excel"] = None
    if isinstance(files.get("csv"), dict):
        files["csv"] = files["csv"].get("files") or files["csv"].get("items") or []
    files.setdefault("csv", [])
    files.setdefault("pdf", None)
    files.setdefault("excel", None)
    return record


def _save_session(session: dict[str, Any]) -> dict[str, Any]:
    session = _session_record(session)
    session["updated_at"] = utc_now_iso()
    session_dir = _session_dir(session)
    session_dir.mkdir(parents=True, exist_ok=True)
    write_json(session_dir / "context.json", session["context"])
    write_json(ACTIVE_SESSION_PATH, session)
    status = quick_session_status(session)
    write_json(_session_status_path(session), status)
    write_json(_validation_preview_path(session), status)
    return session


def _normalize_session_files(session: dict[str, Any]) -> dict[str, Any]:
    files = session.setdefault("files", {"pdf": None, "csv": [], "excel": None})
    if isinstance(files.get("csv"), dict):
        files["csv"] = files["csv"].get("files", [])
    files.setdefault("csv", [])
    files.setdefault("pdf", None)
    files.setdefault("excel", None)
    return session


def active_session(create: bool = True) -> dict[str, Any]:
    payload = _read_json(ACTIVE_SESSION_PATH)
    if payload:
        return _normalize_session_files(payload)
    session = _empty_session()
    return _save_session(session) if create else session


def _file_payload(path: Path, filename: str, status: str = "staged", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "available": True,
        "filename": filename,
        "file_id": filename,
        "path": relative_path(path),
        "status": status,
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if extra:
        payload.update(extra)
    return payload


def _store_file(session: dict[str, Any], upload_type: str, file_storage: FileStorage) -> dict[str, Any]:
    original = file_storage.filename or ""
    filename = secure_filename(original)
    if not filename:
        raise ValueError("Nama file kosong.")
    target_dir = _session_dir(session) / upload_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = (target_dir / filename).resolve()
    if target_dir.resolve() not in target.parents:
        raise ValueError("Path staging tidak valid.")
    file_storage.save(target)
    return _file_payload(target, filename)


def update_session(form: Any, files: Any) -> dict[str, Any]:
    session = active_session(create=True)
    if session.get("status") == "committed":
        session = _empty_session()
    touched_types: set[str] = set()
    payload = {key: form.get(key) for key in form if form.get(key) not in (None, "")}
    if payload:
        session["context"] = normalize_context(payload, base=session.get("context") or read_active_context(), source="upload_session")

    pdf = files.get("pdf") or files.get("file_pdf")
    if pdf and pdf.filename:
        if Path(pdf.filename).suffix.lower() != ".pdf":
            raise ValueError("File PDF harus berekstensi .pdf.")
        session["files"]["pdf"] = _store_file(session, "pdf", pdf)
        touched_types.add("pdf")

    excel = files.get("excel") or files.get("file_excel")
    if excel and excel.filename:
        if Path(excel.filename).suffix.lower() != ".xlsx":
            raise ValueError("File Excel RAB harus berekstensi .xlsx.")
        session["files"]["excel"] = _store_file(session, "excel", excel)
        touched_types.add("excel")

    csv_files = [item for item in [*files.getlist("csv"), *files.getlist("file"), *files.getlist("files")] if item and item.filename]
    for csv_file in csv_files:
        if Path(csv_file.filename).suffix.lower() != ".csv":
            raise ValueError("File transaksi harus berekstensi .csv.")
        item = _store_file(session, "csv", csv_file)
        session["files"]["csv"] = [existing for existing in session["files"].get("csv", []) if existing.get("filename") != item["filename"]]
        session["files"]["csv"].append(item)
        touched_types.add("csv")

    _save_session(session)
    status = quick_session_status(session)
    for upload_type in sorted(touched_types):
        status = validate_uploaded_file_once(status, upload_type)
    return status


def update_context(payload: Any) -> dict[str, Any]:
    session = active_session(create=True)
    if session.get("status") == "committed":
        session = _empty_session()
    supplied = {key: payload.get(key) for key in payload if payload.get(key) not in (None, "")}
    if supplied:
        session["context"] = normalize_context(supplied, base=session.get("context") or read_active_context(), source="upload_session")
        session["context"]["status"] = "draft_saved"
        session["context_status"] = "draft_saved"
    _save_session(session)
    return quick_session_status(session)


def update_file(upload_type: str, files: Any) -> dict[str, Any]:
    if upload_type not in {"pdf", "csv", "excel"}:
        raise ValueError("upload_type harus bernilai pdf, csv, atau excel.")
    form = {"upload_type": upload_type}
    normalized_files: dict[str, Any] = {}
    uploads = files.getlist("file") or files.getlist(upload_type)
    if not uploads:
        raise ValueError("Field file wajib diisi.")
    normalized_files[upload_type] = uploads[0] if upload_type != "csv" else uploads
    if upload_type == "csv":
        class _Files:
            def get(self, _key):
                return None

            def getlist(self, key):
                return uploads if key == "csv" else []

        return update_session(form, _Files())

    class _Files:
        def get(self, key):
            return uploads[0] if key == upload_type else None

        def getlist(self, _key):
            return []

    return update_session(form, _Files())


def remove_file(upload_type: str, filename: str | None = None, file_id: str | None = None) -> dict[str, Any]:
    if upload_type not in {"pdf", "csv", "excel"}:
        raise ValueError("upload_type harus bernilai pdf, csv, atau excel.")
    target_name = secure_filename(filename or file_id or "")
    if not target_name:
        raise ValueError("filename atau file_id wajib diisi.")
    session = active_session(create=True)
    if session.get("status") == "committed":
        session = _empty_session()
    files = session.setdefault("files", {"pdf": None, "csv": [], "excel": None})

    def delete_item(item: dict[str, Any] | None) -> None:
        path = _path_from_item(item)
        if path and path.exists() and STAGING_ROOT.resolve() in path.resolve().parents:
            path.unlink()

    if upload_type == "csv":
        remaining = []
        removed = False
        for item in files.get("csv", []):
            if secure_filename(str(item.get("filename") or item.get("file_id") or "")) == target_name:
                delete_item(item)
                removed = True
            else:
                remaining.append(item)
        files["csv"] = remaining
        if not removed:
            raise ValueError("File CSV tidak ditemukan dalam sesi upload.")
    else:
        item = files.get(upload_type)
        if not item or secure_filename(str(item.get("filename") or item.get("file_id") or "")) != target_name:
            raise ValueError(f"File {upload_type.upper()} tidak ditemukan dalam sesi upload.")
        delete_item(item)
        files[upload_type] = None

    _save_session(session)
    return {**quick_session_status(session), "message": "File dihapus dari sesi upload."}


def _path_from_item(item: dict[str, Any] | None) -> Path | None:
    if not item or not item.get("path"):
        return None
    return ROOT_DIR / item["path"]


def _light_file_errors(item: dict[str, Any] | None, label: str, suffix: str) -> list[str]:
    path = _path_from_item(item)
    if path is None or not path.exists():
        return [f"{label} belum tersedia."]
    if path.suffix.lower() != suffix:
        return [f"File {label} harus berekstensi {suffix}."]
    if path.stat().st_size <= 0:
        return [f"File {label} kosong."]
    return []


def _cached_validation_errors(session: dict[str, Any]) -> dict[str, list[str]]:
    cached = _read_json(_session_status_path(session)) or _read_json(_validation_preview_path(session)) or {}
    errors = cached.get("validation_errors") if isinstance(cached, dict) else None
    if not isinstance(errors, dict):
        return {"pdf": [], "csv": [], "excel": []}
    return {
        "pdf": list(errors.get("pdf") or []),
        "csv": list(errors.get("csv") or []),
        "excel": list(errors.get("excel") or []),
    }


def _validate_pdf(item: dict[str, Any] | None) -> list[str]:
    path = _path_from_item(item)
    if path is None or not path.exists():
        return ["PDF audited belum tersedia."]
    if path.suffix.lower() != ".pdf":
        return ["File PDF harus berekstensi .pdf."]
    if path.stat().st_size <= 0:
        return ["File PDF kosong."]
    try:
        PdfReader(str(path))
    except Exception as exc:
        return [f"File PDF tidak dapat dibaca: {exc}"]
    return []


def _validate_csv_item(item: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    path = _path_from_item(item)
    if path is None or not path.exists():
        return item, ["CSV transaksi tidak ditemukan."]
    errors: list[str] = []
    if path.suffix.lower() != ".csv":
        errors.append("File CSV harus berekstensi .csv.")
    try:
        df = pd.read_csv(path, nrows=5)
        columns = set(df.columns)
        missing = sorted(CSV_REQUIRED_COLUMNS - columns)
        item["columns"] = list(df.columns)
        if missing:
            errors.append(f"Kolom CSV hilang: {', '.join(missing)}")
    except Exception as exc:
        errors.append(f"CSV tidak dapat dibaca: {exc}")
    return item, errors


def _validate_excel(item: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[str]]:
    path = _path_from_item(item)
    if path is None or not path.exists():
        return item, ["Excel RAB belum tersedia."]
    errors: list[str] = []
    if path.suffix.lower() != ".xlsx":
        errors.append("File Excel harus berekstensi .xlsx.")
    try:
        workbook = load_workbook(path, read_only=True, data_only=True)
        if "RAB" not in workbook.sheetnames:
            errors.append("Sheet RAB tidak tersedia.")
        else:
            sheet = workbook["RAB"]
            header = [str(cell.value).strip() if cell.value is not None else "" for cell in next(sheet.iter_rows(min_row=1, max_row=1))]
            missing = sorted(RAB_REQUIRED_COLUMNS - set(header))
            item = {**(item or {}), "sheets": workbook.sheetnames, "columns": header}
            if missing:
                errors.append(f"Kolom RAB hilang: {', '.join(missing)}")
    except Exception as exc:
        errors.append(f"Excel RAB tidak dapat dibaca: {exc}")
    return item, errors


def _build_session_status(session: dict[str, Any], validation_errors: dict[str, list[str]]) -> dict[str, Any]:
    session = session or active_session(create=False)
    session = _normalize_session_files(session)
    files = session.setdefault("files", {"pdf": None, "csv": [], "excel": None})
    pdf_errors = validation_errors.get("pdf") or _light_file_errors(files.get("pdf"), "PDF", ".pdf")
    csv_errors = validation_errors.get("csv") or []
    updated_csv = list(files.get("csv", []))
    if not updated_csv:
        csv_errors = csv_errors or ["CSV transaksi belum tersedia."]
    else:
        for item in updated_csv:
            csv_errors.extend(_light_file_errors(item, "CSV", ".csv"))
    excel_errors = validation_errors.get("excel") or _light_file_errors(files.get("excel"), "Excel", ".xlsx")
    context_ready = bool(session.get("context", {}).get("target_tahun_akademik") and session.get("context", {}).get("target_tahun_anggaran"))
    readiness = {
        "context_ready": context_ready,
        "period_ready": context_ready,
        "pdf_ready": not pdf_errors,
        "csv_ready": bool(updated_csv) and not csv_errors,
        "excel_ready": not excel_errors,
    }
    readiness["can_commit"] = all(readiness.values())
    missing = []
    if not readiness["period_ready"]:
        missing.append("periode data")
    if not readiness["pdf_ready"]:
        missing.append("PDF audited")
    if not readiness["csv_ready"]:
        missing.append("CSV transaksi")
    if not readiness["excel_ready"]:
        missing.append("Excel RAB")
    if session.get("status") == "committed":
        message = "Dataset berhasil di-commit ke Raw Layer. Quality Gate belum dijalankan."
    elif readiness["can_commit"]:
        message = "Semua file wajib tersedia. Data siap diunggah ke Data Lakehouse."
    else:
        message = f"Sesi upload belum lengkap: {', '.join(missing)} belum tersedia."
    status_value = session.get("status", "draft")
    if status_value == "draft" and readiness["can_commit"]:
        status_value = "draft_ready"
    pdf_payload = files.get("pdf") or {"available": False, "items": [], "status": "missing"}
    if files.get("pdf"):
        pdf_payload = {**files["pdf"], "items": [files["pdf"]]}
    csv_payload = {
        "available": bool(updated_csv),
        "count": len(updated_csv),
        "files": updated_csv,
        "items": updated_csv,
        "status": "committed" if session.get("status") == "committed" and updated_csv else "staged" if updated_csv else "missing",
    }
    excel_payload = files.get("excel") or {"available": False, "items": [], "status": "missing"}
    if files.get("excel"):
        excel_payload = {**files["excel"], "items": [files["excel"]]}
    raw_layer = None
    pipeline_state = None
    if session.get("status") == "committed":
        raw_layer = {"status": "ready", "active_dataset_pointer": relative_path(ACTIVE_DATASET_POINTER_PATH)}
        pipeline_state = {
            "quality_gate": "not_started",
            "bronze": "not_started",
            "silver": "not_started",
            "gold": "not_started",
            "metrics": "not_started",
            "dashboard": "not_started",
        }
    return {
        **session,
        "status": status_value,
        "files": {
            "pdf": pdf_payload,
            "csv": csv_payload,
            "excel": excel_payload,
        },
        "readiness": readiness,
        "validation_errors": {"pdf": pdf_errors, "csv": csv_errors, "excel": excel_errors},
        "raw_layer": raw_layer,
        "pipeline_state": pipeline_state,
        "message": message,
    }


def quick_session_status(session: dict[str, Any] | None = None) -> dict[str, Any]:
    session = _session_record(session or active_session(create=False))
    return _build_session_status(session, _cached_validation_errors(session))


def validate_uploaded_file_once(session: dict[str, Any], upload_type: str) -> dict[str, Any]:
    session = _session_record(session)
    session = _normalize_session_files(session)
    cached_errors = _cached_validation_errors(session)
    files = session["files"]
    if upload_type == "pdf":
        cached_errors["pdf"] = _validate_pdf(files.get("pdf"))
    elif upload_type == "csv":
        csv_errors: list[str] = []
        updated_csv = []
        for item in files.get("csv", []):
            updated, errors = _validate_csv_item(dict(item))
            updated_csv.append(updated)
            csv_errors.extend(errors)
        files["csv"] = updated_csv
        cached_errors["csv"] = csv_errors
    elif upload_type == "excel":
        excel_item, excel_errors = _validate_excel(files.get("excel"))
        files["excel"] = excel_item
        cached_errors["excel"] = excel_errors
    status = _build_session_status(session, cached_errors)
    write_json(_session_status_path(session), status)
    write_json(_validation_preview_path(session), status)
    return status


def validate_session_for_commit(session: dict[str, Any] | None = None) -> dict[str, Any]:
    session = _session_record(session or active_session(create=False))
    session = _normalize_session_files(session)
    files = session["files"]
    pdf_errors = _validate_pdf(files.get("pdf"))
    csv_errors: list[str] = []
    updated_csv = []
    for item in files.get("csv", []):
        updated, errors = _validate_csv_item(dict(item))
        updated_csv.append(updated)
        csv_errors.extend(errors)
    excel_item, excel_errors = _validate_excel(files.get("excel"))
    files["csv"] = updated_csv
    files["excel"] = excel_item
    status = _build_session_status(session, {"pdf": pdf_errors, "csv": csv_errors, "excel": excel_errors})
    write_json(_session_status_path(session), status)
    write_json(_validation_preview_path(session), status)
    return status


def session_status(session: dict[str, Any] | None = None) -> dict[str, Any]:
    return quick_session_status(session)


def _target_path(session: dict[str, Any], upload_type: str, item: dict[str, Any]) -> Path:
    context = session["context"]
    prefix = f"{session['session_id']}_{secure_filename(item['filename'])}"
    if upload_type == "pdf":
        return DATA_DIR / "raw" / "pdf" / _safe_period(context.get("target_tahun_anggaran")) / prefix
    if upload_type == "excel":
        return DATA_DIR / "raw" / "excel" / _safe_period(context.get("target_tahun_anggaran")) / prefix
    return DATA_DIR / "raw" / "csv" / _safe_period(context.get("target_tahun_akademik")) / prefix


def _copy_item(session: dict[str, Any], upload_type: str, item: dict[str, Any]) -> dict[str, Any]:
    source = _path_from_item(item)
    if source is None:
        raise FileNotFoundError(item.get("filename", upload_type))
    target = _target_path(session, upload_type, item)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return {**item, "canonical_path": relative_path(target), "status": "committed"}


def _write_registry(session: dict[str, Any], pointer: dict[str, Any]) -> None:
    previous = _read_json(UPLOAD_REGISTRY_PATH) or {}
    previous_sessions = [item for item in previous.get("sessions", []) if item.get("session_id") != session["session_id"]]
    registry = {
        "active_session_id": session["session_id"],
        "active": {
            "pdf": session["files"]["pdf"],
            "csv": session["files"]["csv"]["files"],
            "excel": session["files"]["excel"],
        },
        "sessions": [session, *previous_sessions],
        "files": {
            "pdf": [session["files"]["pdf"]],
            "csv": session["files"]["csv"]["files"],
            "excel": [session["files"]["excel"]],
        },
        "dataset_pointer": pointer,
        "updated_at": utc_now_iso(),
    }
    write_json(UPLOAD_REGISTRY_PATH, registry)


def _dataset_entry(session: dict[str, Any], pointer: dict[str, Any]) -> dict[str, Any]:
    context = session.get("context") or {}
    return {
        "dataset_id": session["session_id"],
        "session_id": session["session_id"],
        "status": "committed",
        "target_prodi": context.get("target_prodi"),
        "target_fakultas": context.get("target_fakultas"),
        "tahun_akademik": context.get("target_tahun_akademik"),
        "tahun_anggaran": context.get("target_tahun_anggaran"),
        "target_label": context.get("target_label"),
        "committed_at": session.get("committed_at"),
        "raw_paths": {
            "pdf": pointer.get("active_pdf"),
            "csv": pointer.get("active_csv_files") or [],
            "excel": pointer.get("active_excel"),
        },
        "dataset_pointer": pointer,
    }


def _write_dataset_registry(session: dict[str, Any], pointer: dict[str, Any]) -> None:
    existing = _read_json(DATASET_REGISTRY_PATH) or {}
    datasets = [item for item in existing.get("datasets", []) if item.get("session_id") != session["session_id"]]
    entry = _dataset_entry(session, pointer)
    datasets = [entry, *datasets]
    registry = {
        "active_dataset_id": entry["dataset_id"],
        "active_session_id": session["session_id"],
        "updated_at": utc_now_iso(),
        "datasets": datasets,
    }
    write_json(DATASET_REGISTRY_PATH, registry)
    periods = []
    seen = set()
    for item in datasets:
        key = (item.get("tahun_akademik"), item.get("tahun_anggaran"), item.get("target_prodi"))
        if key in seen or not any(key):
            continue
        seen.add(key)
        periods.append(
            {
                "dataset_id": item.get("dataset_id"),
                "session_id": item.get("session_id"),
                "tahun_akademik": item.get("tahun_akademik"),
                "tahun_anggaran": item.get("tahun_anggaran"),
                "target_prodi": item.get("target_prodi"),
                "target_fakultas": item.get("target_fakultas"),
                "status": item.get("status"),
            }
        )
    write_json(AVAILABLE_PERIODS_PATH, {"updated_at": utc_now_iso(), "periods": periods})


def _write_post_commit_truth(session: dict[str, Any]) -> None:
    payload = {
        "generated_at": utc_now_iso(),
        "dataset_mode": "uploaded",
        "upload_session": {"session_id": session["session_id"], "status": "committed"},
        "layers": {
            "raw": {"status": "ready", "message": "Raw layer berisi sesi upload committed."},
            "quality_gate": {"status": "not_started", "message": "Quality Gate belum dijalankan."},
            "bronze": {"status": "not_started", "message": "Bronze belum tersedia."},
            "silver": {"status": "not_started", "message": "Silver belum tersedia."},
            "gold": {"status": "not_started", "message": "Gold belum tersedia."},
            "metrics": {"status": "not_started", "message": "Metrics belum tersedia."},
            "dashboard": {"status": "not_started", "message": "Dashboard belum diperbarui."},
        },
        "uat": {"status": "manual_input_required", "message": "UAT membutuhkan input manual."},
    }
    write_json(SYSTEM_TRUTH_STATUS_PATH, payload)


def commit_session() -> dict[str, Any]:
    status = validate_session_for_commit(active_session(create=False))
    if not status["readiness"]["can_commit"]:
        status["status"] = "commit_failed"
        status["commit_status"] = "commit_failed"
        _save_session(status)
        return {**status, "message": "Commit gagal. Lengkapi atau perbaiki file wajib sebelum commit."}

    copied: list[Path] = []
    try:
        pdf = _copy_item(status, "pdf", status["files"]["pdf"])
        copied.append(ROOT_DIR / pdf["canonical_path"])
        csv_items = []
        for item in status["files"]["csv"]["files"]:
            copied_csv = _copy_item(status, "csv", item)
            csv_items.append(copied_csv)
            copied.append(ROOT_DIR / copied_csv["canonical_path"])
        excel = _copy_item(status, "excel", status["files"]["excel"])
        copied.append(ROOT_DIR / excel["canonical_path"])
    except Exception as exc:
        for path in copied:
            if path.exists():
                path.unlink()
        failed = {**status, "status": "commit_failed", "commit_status": "commit_failed", "message": f"Commit gagal dan tidak ada file dipindahkan sebagian: {exc}"}
        _save_session(failed)
        return failed

    status["files"] = {
        "pdf": pdf,
        "csv": {"available": True, "count": len(csv_items), "files": csv_items, "items": csv_items, "status": "committed"},
        "excel": excel,
    }
    status["status"] = "committed"
    status["commit_status"] = "committed"
    status["committed_at"] = utc_now_iso()
    pointer = {
        "dataset_mode": "uploaded",
        "session_id": status["session_id"],
        "active_pdf": pdf["canonical_path"],
        "active_csv_files": [item["canonical_path"] for item in csv_items],
        "active_excel": excel["canonical_path"],
        "target_prodi": status["context"].get("target_prodi"),
        "target_fakultas": status["context"].get("target_fakultas"),
        "tahun_akademik": status["context"].get("target_tahun_akademik"),
        "tahun_anggaran": status["context"].get("target_tahun_anggaran"),
        "target_label": status["context"].get("target_label"),
        "context_source": "upload_session",
        "status": "committed",
        "created_at": utc_now_iso(),
    }
    write_json(ACTIVE_DATASET_POINTER_PATH, pointer)
    write_json(
        LATEST_UPLOAD_METADATA_PATH,
        {
            "session_id": status["session_id"],
            "status": "committed",
            "context": status["context"],
            "files": {"pdf": pdf, "csv": csv_items, "excel": excel},
            "committed_at": status["committed_at"],
            "raw_paths": {
                "pdf": pdf["canonical_path"],
                "csv": [item["canonical_path"] for item in csv_items],
                "excel": excel["canonical_path"],
            },
            "dataset_pointer": pointer,
            "message": "Sesi upload berhasil di-commit ke Raw Layer.",
        },
    )
    _write_registry(status, pointer)
    _write_dataset_registry(status, pointer)
    write_active_context(status["context"], source="upload_session")
    _write_post_commit_truth(status)
    _save_session(status)
    return {**quick_session_status(status), "dataset_pointer": pointer, "message": "Dataset berhasil di-commit ke Raw Layer. Quality Gate belum dijalankan."}


def reset_session() -> dict[str, Any]:
    session = active_session(create=False)
    session_dir = _session_dir(session)
    if session_dir.exists() and session.get("status") != "committed":
        shutil.rmtree(session_dir, ignore_errors=True)
    if ACTIVE_SESSION_PATH.exists():
        ACTIVE_SESSION_PATH.unlink()
    return quick_session_status(active_session(create=True))
