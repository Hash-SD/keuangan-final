from __future__ import annotations

import os
import json
from pathlib import Path

from src.common.paths import RAW_DIR
from src.common.runtime_config import get_runtime_config

ACTIVE_DATASET_POINTER = Path(__file__).resolve().parents[2] / "outputs" / "reports" / "active_dataset_pointer.json"


def _env_filename(name: str, default: str) -> str:
    value = os.getenv(name)
    filename = Path(value.strip()).name if value and value.strip() else default
    return filename or default


def active_dataset_pointer() -> dict | None:
    if not ACTIVE_DATASET_POINTER.exists():
        return None
    try:
        payload = json.loads(ACTIVE_DATASET_POINTER.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or payload.get("status") != "committed":
        return None
    return payload


def dataset_mode() -> str:
    return "uploaded_excel"


def _pointer_path(key: str) -> Path | None:
    pointer = active_dataset_pointer()
    value = pointer.get(key) if pointer else None
    if not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = Path(__file__).resolve().parents[2] / path
    return path if path.exists() else None


def raw_rab_path() -> Path:
    active = _pointer_path("active_excel")
    if active is not None:
        return active
    return RAW_DIR / "excel" / _env_filename("PORTAL_RAB_FILENAME", "rab_prodi_sains_data.xlsx")


def active_period_metadata() -> dict[str, str]:
    config = get_runtime_config()
    pointer = active_dataset_pointer() or {}
    target_prodi = pointer.get("target_prodi") or config.target_prodi
    target_fakultas = pointer.get("target_fakultas") or config.target_fakultas
    target_tahun_akademik = pointer.get("tahun_akademik") or config.target_tahun_akademik
    target_tahun_anggaran = pointer.get("tahun_anggaran") or config.target_tahun_anggaran
    return {
        "target_prodi": target_prodi,
        "target_fakultas": target_fakultas,
        "target_tahun_akademik": target_tahun_akademik,
        "target_tahun_anggaran": target_tahun_anggaran,
        "target_label": pointer.get("target_label") or f"{target_prodi} - Tahun Akademik {target_tahun_akademik}",
        "batch_id": pointer.get("batch_id") or config.batch_id,
        "source_event": config.source_event_iso,
    }
