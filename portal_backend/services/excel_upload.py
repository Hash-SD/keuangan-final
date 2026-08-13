from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4
import hashlib
import json
import re
import shutil

from openpyxl import load_workbook

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from .files import read_json, relative_path, write_json
from .paths import DATA_DIR, OUTPUTS_DIR, ROOT_DIR
from src.common.time_utils import utc_now_iso
from src.common.workbook_kind import infer_workbook_kind
from src.validation.dataset_contract import validate_committed_dataset


ACTIVE_EXCEL_DATASET_PATH = OUTPUTS_DIR / "reports" / "active_excel_lakehouse_dataset.json"
EXCEL_DATASET_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "excel_dataset_registry.json"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def _safe(value: object, fallback: str = "unknown") -> str:
    return secure_filename(str(value or fallback).replace("/", "-")) or fallback


def _kind(filename: str, explicit: str | None = None) -> str:
    return infer_workbook_kind(filename, explicit)


def normalize_dataset_file_kinds(payload: dict[str, Any] | None) -> dict[str, Any]:
    """Return a dataset copy with obvious filename/category mismatches repaired."""

    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        return payload or {}
    normalized_files: list[Any] = []
    changed = False
    for item in payload["files"]:
        if not isinstance(item, dict):
            normalized_files.append(item)
            continue
        normalized_kind = _kind(
            str(item.get("filename") or Path(str(item.get("path") or "")).name),
            str(item.get("jenis_dataset") or "") or None,
        )
        normalized_item = {**item, "jenis_dataset": normalized_kind}
        normalized_files.append(normalized_item)
        changed = changed or normalized_item != item
    refreshed_scope = _upload_scope(
        normalized_files,
        str(payload.get("tahun_input") or "").strip() or None,
    )
    scope_changed = any(payload.get(key) != value for key, value in refreshed_scope.items())
    return {**payload, "files": normalized_files, **refreshed_scope} if changed or scope_changed else payload


def _detect_year(filename: str, fallback: str | None) -> str | None:
    match = re.search(r"(?<!\d)(20\d{2})(?!\d)", filename)
    return match.group(1) if match else fallback


def _upload_scope(saved: list[dict[str, Any]], tahun_input: str | None) -> dict[str, Any]:
    years = sorted(
        {
            year
            for item in saved
            if (
                year := _detect_year(
                    str(item["filename"]),
                    str(item.get("tahun_input") or tahun_input or "") or None,
                )
            )
        }
    )
    kinds = {str(item.get("jenis_dataset") or "") for item in saved}
    has_nomenklatur = "nomenklatur" in kinds
    has_2025_like = any(
        "2025" in str(item["filename"])
        or _detect_year(
            str(item["filename"]),
            str(item.get("tahun_input") or tahun_input or "") or None,
        )
        == "2025"
        for item in saved
    )
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


def _parse_file_metadata(raw_value: str, expected_count: int) -> list[dict[str, Any]] | None:
    if not raw_value:
        return None
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise ValueError("Metadata setiap file tidak valid.") from exc
    if not isinstance(parsed, list) or len(parsed) != expected_count or any(
        not isinstance(item, dict) for item in parsed
    ):
        raise ValueError("Metadata setiap file harus berjumlah sama dengan file yang dipilih.")
    return [dict(item) for item in parsed]


def _common_metadata_value(records: list[dict[str, Any]], key: str) -> str | None:
    values = {str(record.get(key) or "").strip() for record in records}
    values.discard("")
    return next(iter(values)) if len(values) == 1 else None


def _build_upload_metadata_records(
    form: Any,
    upload_count: int,
    upload_mode: str,
    legacy_metadata: bool,
    jenis_dataset: str | None,
    raw_tahun_input: str,
    raw_periode: str,
    raw_prodi: str,
    raw_fakultas: str,
) -> list[dict[str, Any]]:
    entries = _parse_file_metadata(
        str(form.get("file_metadata") or "").strip(),
        upload_count,
    )
    records: list[dict[str, Any]] = []
    for index in range(upload_count):
        entry = entries[index] if entries is not None else {}
        item_mode = str(entry.get("upload_mode") or upload_mode).strip().lower()
        if item_mode != upload_mode:
            raise ValueError("Semua file dalam satu antrean harus memakai mode upload yang sama.")
        item_kind = str(entry.get("jenis_dataset") or jenis_dataset or "").strip().lower() or None
        item_tahun = str(entry.get("tahun_input") or raw_tahun_input).strip()
        item_periode = str(entry.get("periode") or raw_periode).strip()
        item_prodi = str(entry.get("prodi") or raw_prodi).strip()
        item_fakultas = str(entry.get("fakultas") or raw_fakultas).strip()
        if item_mode == "multi":
            records.append(
                {
                    "upload_mode": "multi",
                    "jenis_dataset": item_kind,
                    "tahun_input": None,
                    "periode": None,
                    "prodi": None,
                    "fakultas": None,
                }
            )
            continue
        missing_metadata = [
            label
            for label, value in (
                ("Tahun Input", item_tahun),
                ("Periode", item_periode),
                ("Prodi", item_prodi),
                ("Fakultas", item_fakultas),
            )
            if not value
        ]
        if missing_metadata and not legacy_metadata:
            raise ValueError(
                f"Metadata upload single pada file ke-{index + 1} wajib diisi: "
                + ", ".join(missing_metadata)
                + "."
            )
        records.append(
            {
                "upload_mode": "single",
                "jenis_dataset": item_kind,
                "tahun_input": item_tahun or None,
                "periode": item_periode or ("Tahunan" if legacy_metadata else None),
                "prodi": item_prodi or ("Sains Data" if legacy_metadata else None),
                "fakultas": item_fakultas or ("Fakultas Sains" if legacy_metadata else None),
            }
        )
    return records


def commit_excel_lakehouse_dataset(form: Any, files: Any) -> dict[str, Any]:
    upload_started_at = utc_now_iso()
    uploads: list[FileStorage] = []
    for key in ["file_excel", "file_excel[]", "excel", "files", "file"]:
        uploads.extend([item for item in files.getlist(key) if item and item.filename])
    if not uploads:
        raise ValueError("Minimal satu file Excel wajib diunggah.")

    jenis_dataset = str(form.get("jenis_dataset") or "").strip().lower() or None
    raw_upload_mode = str(form.get("upload_mode") or "").strip().lower()
    legacy_metadata = not raw_upload_mode
    upload_mode = raw_upload_mode or ("multi" if jenis_dataset == "rpd" else "single")
    if upload_mode not in {"single", "multi"}:
        raise ValueError("Mode upload tidak valid. Gunakan single atau multi.")

    raw_tahun_input = str(form.get("tahun_input") or form.get("tahun_anggaran") or "").strip()
    raw_periode = str(form.get("periode") or "").strip()
    raw_prodi = str(form.get("prodi") or "").strip()
    raw_fakultas = str(form.get("fakultas") or "").strip()
    metadata_records = _build_upload_metadata_records(
        form,
        len(uploads),
        upload_mode,
        legacy_metadata,
        jenis_dataset,
        raw_tahun_input,
        raw_periode,
        raw_prodi,
        raw_fakultas,
    )
    tahun_input = _common_metadata_value(metadata_records, "tahun_input")
    periode = _common_metadata_value(metadata_records, "periode")
    prodi = _common_metadata_value(metadata_records, "prodi")
    fakultas = _common_metadata_value(metadata_records, "fakultas")
    dataset_jenis_dataset = _common_metadata_value(metadata_records, "jenis_dataset")
    metadata_mixed = len(
        {
            tuple(record.get(key) for key in ("upload_mode", "tahun_input", "periode", "prodi", "fakultas"))
            for record in metadata_records
        }
    ) > 1
    metadata_years = sorted(
        {
            str(record["tahun_input"])
            for record in metadata_records
            if record.get("tahun_input")
        }
    )
    target_year = (
        metadata_years[0]
        if len(metadata_years) == 1
        else "multi-year"
        if metadata_years
        else "unknown"
    )
    catatan = str(form.get("catatan") or "").strip() or None
    append_to_active = str(form.get("append_to_active") or "").strip().lower() == "true"
    dashboard_mode = str(form.get("dashboard_mode") or "update").strip().lower()
    if dashboard_mode not in {"update", "new"}:
        dashboard_mode = "update"
    dashboard_database_id = str(form.get("dashboard_database_id") or "").strip()
    if dashboard_database_id and not dashboard_database_id.isdigit():
        raise ValueError("Database target Superset tidak valid.")
    dashboard_database_id = dashboard_database_id or None
    dashboard_dashboard_id = str(form.get("dashboard_dashboard_id") or "").strip()
    if dashboard_dashboard_id and not dashboard_dashboard_id.isdigit():
        raise ValueError("Dashboard target Superset tidak valid.")
    dashboard_dashboard_id = dashboard_dashboard_id or None
    dataset_id = f"excel-{utc_now_iso().replace(':', '').replace('-', '').split('.')[0]}-{uuid4().hex[:6]}"
    if len(uploads) > 20:
        raise ValueError("Jumlah workbook melebihi batas 20 file per dataset.")
    staging_dir = DATA_DIR / "uploads" / "staging" / dataset_id
    target_dir = DATA_DIR / "raw" / "excel_lakehouse" / _safe(target_year, "unknown") / dataset_id
    saved: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    try:
        staging_dir.mkdir(parents=True, exist_ok=False)
        for index, upload in enumerate(uploads):
            metadata = metadata_records[index]
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
                    "jenis_dataset": _kind(
                        filename,
                        None if metadata["upload_mode"] == "multi" else metadata.get("jenis_dataset"),
                    ),
                    "upload_mode": metadata["upload_mode"],
                    "tahun_input": metadata["tahun_input"],
                    "periode": metadata["periode"],
                    "prodi": metadata["prodi"],
                    "fakultas": metadata["fakultas"],
                }
            )
        active = (
            normalize_dataset_file_kinds(read_json(ACTIVE_EXCEL_DATASET_PATH))
            if append_to_active
            else None
        )
        active_files = active.get("files", []) if isinstance(active, dict) and active.get("status") == "committed" else []
        if active_files:
            first_path = Path(str(active_files[0].get("path") or ""))
            existing_dir = first_path.parent if first_path.is_absolute() else (ROOT_DIR / first_path).parent
            if not existing_dir.exists():
                raise ValueError("Dataset aktif tidak dapat ditambah karena direktori sumber tidak tersedia.")
            for item in saved:
                if (existing_dir / str(item["filename"])).exists():
                    raise ValueError(f"Nama workbook {item['filename']} sudah ada pada dataset aktif.")
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
        "upload_mode": upload_mode,
        "metadata_scope": "bundle" if upload_mode == "multi" else "per_file",
        "metadata_mixed": metadata_mixed,
        "tahun_input": tahun_input or None,
        "periode": periode,
        "prodi": prodi,
        "fakultas": fakultas,
        "jenis_dataset": dataset_jenis_dataset or jenis_dataset,
        "catatan": catatan,
        "dashboard_mode": dashboard_mode,
        "dashboard_database_id": dashboard_database_id,
        "dashboard_dashboard_id": dashboard_dashboard_id,
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


def _active_raw_root() -> Path:
    return (DATA_DIR / "raw" / "excel_lakehouse").resolve()


def _resolve_active_file_path(file_record: dict[str, Any]) -> Path:
    raw_path = str(file_record.get("path") or "").strip()
    if not raw_path:
        raise ValueError("Metadata file aktif tidak memiliki path.")
    candidate = Path(raw_path)
    resolved = (candidate if candidate.is_absolute() else ROOT_DIR / candidate).resolve()
    try:
        resolved.relative_to(_active_raw_root())
    except ValueError as exc:
        raise ValueError("File aktif berada di luar canonical raw root.") from exc
    return resolved


def _read_active_dataset() -> dict[str, Any]:
    active = normalize_dataset_file_kinds(read_json(ACTIVE_EXCEL_DATASET_PATH))
    if not isinstance(active, dict) or active.get("status") != "committed":
        raise FileNotFoundError("Dataset aktif COMMITTED tidak tersedia.")
    files = active.get("files")
    if not isinstance(files, list) or not files:
        raise FileNotFoundError("Dataset aktif tidak memiliki file.")
    return active


def _validate_after_file_change(dataset: dict[str, Any]) -> dict[str, Any]:
    validation = validate_committed_dataset(dataset, ROOT_DIR)
    return {
        "validation_status": "VALIDATED" if validation["valid"] else "NEEDS_REVIEW",
        "validation_errors": validation["errors"],
    }


def _persist_file_change(
    active: dict[str, Any],
    remaining_files: list[dict[str, Any]],
    deleted_files: list[dict[str, Any]],
) -> dict[str, Any]:
    dataset_id = str(active.get("dataset_session_id") or active.get("dataset_id") or "").strip()
    if not dataset_id:
        raise ValueError("Dataset aktif tidak memiliki dataset_session_id.")
    now = utc_now_iso()
    if remaining_files:
        updated = {
            **active,
            **_upload_scope(remaining_files, str(active.get("tahun_input") or "") or None),
            **_validate_after_file_change({**active, "files": remaining_files}),
            "files": remaining_files,
            "status": "committed",
            "upload_state": "COMMITTED",
            "updated_at": now,
            "deleted_files": [*(active.get("deleted_files") or []), *deleted_files],
        }
        write_json(ACTIVE_EXCEL_DATASET_PATH, updated)
        active_dataset_id: str | None = dataset_id
        registry_record = updated
    else:
        updated = {
            "dataset_id": None,
            "dataset_session_id": None,
            "deleted_dataset_id": dataset_id,
            "status": "empty",
            "upload_state": "EMPTY",
            "validation_status": "DELETED",
            "files": [],
            "deleted_files": [*(active.get("deleted_files") or []), *deleted_files],
            "deleted_at": now,
            "updated_at": now,
        }
        write_json(ACTIVE_EXCEL_DATASET_PATH, updated)
        active_dataset_id = None
        registry_record = {
            **active,
            "status": "DELETED",
            "upload_state": "DELETED",
            "validation_status": "DELETED",
            "files": [],
            "deleted_files": updated["deleted_files"],
            "deleted_at": now,
            "updated_at": now,
        }

    registry = read_json(EXCEL_DATASET_REGISTRY_PATH) or {}
    datasets = registry.get("datasets") if isinstance(registry, dict) else []
    datasets = datasets if isinstance(datasets, list) else []
    registry = {
        **registry,
        "active_dataset_id": active_dataset_id,
        "updated_at": now,
        "datasets": [
            registry_record,
            *[
                item
                for item in datasets
                if str(item.get("dataset_id") or item.get("dataset_session_id") or "") != dataset_id
            ],
        ],
    }
    write_json(EXCEL_DATASET_REGISTRY_PATH, registry)
    return updated


def delete_active_dataset_file(filename: str) -> dict[str, Any]:
    requested = str(filename or "").strip()
    if not requested or Path(requested).name != requested:
        raise ValueError("Nama file aktif tidak valid.")
    active = _read_active_dataset()
    files = [item for item in active["files"] if isinstance(item, dict)]
    match = next((item for item in files if str(item.get("filename") or "") == requested), None)
    if match is None:
        raise FileNotFoundError(f"File {requested!r} tidak ditemukan pada dataset aktif.")
    target = _resolve_active_file_path(match)
    physical_deleted = target.is_file()
    if physical_deleted:
        target.unlink()
    try:
        target.parent.rmdir()
    except OSError:
        pass
    deleted = {
        **match,
        "deleted_at": utc_now_iso(),
        "physical_deleted": physical_deleted,
    }
    remaining = [item for item in files if item is not match]
    updated = _persist_file_change(active, remaining, [deleted])
    return {
        **updated,
        "deleted_file": deleted,
        "deleted_file_count": 1,
        "committed_file_count": len(remaining),
    }


def delete_all_active_dataset_files() -> dict[str, Any]:
    active = _read_active_dataset()
    files = [item for item in active["files"] if isinstance(item, dict)]
    targets = [(item, _resolve_active_file_path(item)) for item in files]
    deleted_at = utc_now_iso()
    deleted_files: list[dict[str, Any]] = []
    for item, target in targets:
        physical_deleted = target.is_file()
        if physical_deleted:
            target.unlink()
        deleted_files.append({**item, "deleted_at": deleted_at, "physical_deleted": physical_deleted})
    for _, target in targets:
        try:
            target.parent.rmdir()
        except OSError:
            pass
    updated = _persist_file_change(active, [], deleted_files)
    return {
        **updated,
        "deleted_files": deleted_files,
        "deleted_file_count": len(deleted_files),
        "committed_file_count": 0,
    }
