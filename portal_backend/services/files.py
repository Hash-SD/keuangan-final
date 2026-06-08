from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from werkzeug.utils import secure_filename

from .paths import DEFAULT_PREVIEW_FILES, OUTPUTS_DIR, PREVIEW_LAYER_DIRS, ROOT_DIR, UPLOAD_DIRS


UPLOAD_REGISTRY_PATH = OUTPUTS_DIR / "reports" / "upload_registry.json"


def relative_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT_DIR).as_posix()


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_error": str(exc)}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_registry() -> dict[str, Any]:
    payload = read_json(UPLOAD_REGISTRY_PATH)
    if isinstance(payload, dict) and not payload.get("_error"):
        payload.setdefault("active", {})
        payload.setdefault("files", {"pdf": [], "csv": [], "excel": []})
        return payload
    return {"active": {}, "files": {"pdf": [], "csv": [], "excel": []}}


def record_upload(result: dict[str, Any]) -> None:
    if result.get("status") != "success":
        return
    upload_type = result.get("type")
    if upload_type not in UPLOAD_DIRS:
        return
    registry = upload_registry()
    registry.setdefault("active", {})
    registry.setdefault("files", {}).setdefault(upload_type, [])
    item = {
        key: value
        for key, value in result.items()
        if key not in {"preview"} and value is not None
    }
    existing = [entry for entry in registry["files"][upload_type] if entry.get("path") != item.get("path")]
    registry["files"][upload_type] = [item, *existing][:20]
    if upload_type == "csv":
        registry["active"]["csv"] = registry["files"][upload_type][:2]
    else:
        registry["active"][upload_type] = item
    write_json(UPLOAD_REGISTRY_PATH, registry)


def update_active_upload_context(period: dict[str, Any]) -> None:
    if not period:
        return
    registry = upload_registry()
    active = registry.get("active", {})
    active_paths: set[str] = set()

    for upload_type, value in list(active.items()):
        if upload_type == "csv" and isinstance(value, list):
            updated_files = []
            for item in value:
                if isinstance(item, dict):
                    item = {**item, **period}
                    if item.get("path"):
                        active_paths.add(item["path"])
                updated_files.append(item)
            active[upload_type] = updated_files
        elif isinstance(value, dict):
            active[upload_type] = {**value, **period}
            if value.get("path"):
                active_paths.add(value["path"])

    for upload_type, files in registry.get("files", {}).items():
        if not isinstance(files, list):
            continue
        registry["files"][upload_type] = [
            {**item, **period} if isinstance(item, dict) and item.get("path") in active_paths else item
            for item in files
        ]

    registry["active"] = active
    write_json(UPLOAD_REGISTRY_PATH, registry)


def csv_preview(path: Path, limit: int = 10) -> dict[str, Any]:
    limit = max(1, min(int(limit), 25))
    if not path.exists():
        return {
            "available": False,
            "message": f"File tidak ditemukan: {relative_path(path)}",
            "columns": [],
            "rows": [],
            "limit": limit,
        }
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            rows = [row for _, row in zip(range(limit), reader)]
        return {
            "available": True,
            "path": relative_path(path),
            "columns": columns,
            "rows": rows,
            "limit": limit,
        }
    except OSError as exc:
        return {"available": False, "message": str(exc), "columns": [], "rows": [], "limit": limit}


def resolve_preview_file(layer: str, filename: str | None) -> Path | None:
    base = PREVIEW_LAYER_DIRS.get(layer)
    if base is None:
        return None
    if filename:
        candidate = (base / secure_filename(filename)).resolve()
    elif layer in DEFAULT_PREVIEW_FILES:
        candidate = (base / DEFAULT_PREVIEW_FILES[layer]).resolve()
    else:
        candidate = next((item.resolve() for item in base.glob("*.csv")), None)
        if candidate is None:
            return None
    base_resolved = base.resolve()
    if candidate != base_resolved and base_resolved not in candidate.parents:
        return None
    return candidate


def save_upload(file_storage, upload_type: str, allowed_extensions: set[str], period: dict[str, Any] | None = None) -> dict[str, Any]:
    original = file_storage.filename or ""
    filename = secure_filename(original)
    suffix = Path(filename).suffix.lower()
    if not filename:
        return {"status": "failed", "message": "Nama file kosong."}
    if suffix not in allowed_extensions:
        return {"status": "failed", "message": f"Ekstensi tidak didukung: {suffix}"}
    target_dir = UPLOAD_DIRS[upload_type]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = (target_dir / filename).resolve()
    if target_dir.resolve() not in target.parents:
        return {"status": "failed", "message": "Path upload tidak valid."}
    file_storage.save(target)
    period = period or {}
    response = {
        "status": "success",
        "type": upload_type,
        "filename": filename,
        "path": relative_path(target),
        **period,
    }
    write_json(
        OUTPUTS_DIR / "reports" / "latest_upload_metadata.json",
        {
            **period,
            "type": upload_type,
            "filename": filename,
            "path": relative_path(target),
        },
    )
    if upload_type == "csv":
        response["preview"] = csv_preview(target, limit=10)
    record_upload(response)
    return response
