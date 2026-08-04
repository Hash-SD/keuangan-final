from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.common.workbook_kind import infer_workbook_kind


EXCEL_SUFFIXES = {".xlsx", ".xlsm", ".xltx", ".xltm"}
FORBIDDEN_PATH_PARTS = {"fixture", "fixtures", "synthetic", "sample", "dummy", "test-session", "archive"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_committed_dataset(payload: dict[str, Any], root_dir: Path) -> dict[str, Any]:
    """Validate the active uploaded dataset before any Bronze work starts."""
    errors: list[str] = []
    dataset_id = str(payload.get("dataset_session_id") or payload.get("dataset_id") or "").strip()
    if payload.get("status") != "committed" or payload.get("upload_state") != "COMMITTED":
        errors.append("dataset aktif bukan COMMITTED")
    if not dataset_id:
        errors.append("dataset_session_id tidak tersedia")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        errors.append("dataset aktif tidak memiliki daftar file")
        files = []

    resolved_files: list[dict[str, Any]] = []
    kinds: set[str] = set()
    for item in files:
        if not isinstance(item, dict):
            errors.append("metadata file dataset tidak valid")
            continue
        raw_path = str(item.get("path") or "").strip()
        path = Path(raw_path)
        path = path if path.is_absolute() else root_dir / path
        try:
            path = path.resolve()
            path.relative_to(root_dir.resolve())
        except ValueError:
            errors.append(f"path file di luar repository: {raw_path}")
            continue
        canonical_root = (root_dir / "data" / "raw" / "excel_lakehouse").resolve()
        if canonical_root.exists():
            try:
                path.relative_to(canonical_root)
            except ValueError:
                errors.append(f"path file bukan canonical raw: {raw_path}")
                continue
        if any(part.lower() in FORBIDDEN_PATH_PARTS for part in path.parts):
            errors.append(f"artefak non-produksi tidak boleh menjadi sumber canonical: {raw_path}")
        if path.suffix.lower() not in EXCEL_SUFFIXES:
            errors.append(f"file bukan workbook Excel: {raw_path}")
        if not path.is_file():
            errors.append(f"file sumber tidak ditemukan: {raw_path}")
            continue
        expected_hash = str(item.get("sha256") or "").strip().lower()
        actual_hash = _sha256(path)
        if expected_hash and expected_hash != actual_hash:
            errors.append(f"checksum file tidak cocok: {raw_path}")
        kind = infer_workbook_kind(path.name, item.get("jenis_dataset"))
        kinds.add(kind)
        # This result is emitted by Airflow as JSON; keep paths portable and
        # serializable instead of leaking pathlib objects across the boundary.
        resolved_files.append({"metadata": item, "path": str(path), "sha256": actual_hash, "jenis_dataset": kind})

    if "rab" not in kinds and "rpd" not in kinds:
        errors.append("dataset canonical wajib memiliki workbook RAB")
    if "nomenklatur" not in kinds:
        errors.append("dataset canonical wajib memiliki workbook Nomenklatur")

    return {
        "valid": not errors,
        "errors": errors,
        "dataset_session_id": dataset_id or None,
        "files": resolved_files,
        "file_count": len(resolved_files),
        "kinds": sorted(kinds),
    }


def validate_active_dataset_file(path: Path, root_dir: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"valid": False, "errors": [f"pointer dataset tidak dapat dibaca: {exc}"]}
    return validate_committed_dataset(payload, root_dir)
