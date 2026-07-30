from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR, ROOT_DIR
from src.common.runtime_config import get_runtime_config


CORE_GOLD_ARTIFACTS = [
    "data/generated/gold/fact_anggaran.csv",
    "data/generated/gold/vw_dashboard_iku_anggaran.csv",
    "data/generated/gold/vw_dashboard_detail_item.csv",
    "data/generated/excel_lakehouse_metadata.json",
]


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _mtime(path: Path) -> datetime | None:
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)


def _latest_existing_mtime(paths: list[Path]) -> datetime | None:
    values = [_mtime(path) for path in paths]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _resolve_path(base_dir: Path, value: Any) -> Path | None:
    if not value:
        return None
    path = Path(str(value))
    return path if path.is_absolute() else base_dir / path


def _active_source_ready_time(base_dir: Path, config_source_event: datetime) -> tuple[datetime, str, str | None]:
    excel_pointer = _read_json(base_dir / "outputs" / "reports" / "active_excel_lakehouse_dataset.json")
    if excel_pointer and excel_pointer.get("status") == "committed":
        source_paths = [
            _resolve_path(base_dir, item.get("path"))
            for item in excel_pointer.get("files", [])
            if isinstance(item, dict)
        ]
        source_mtimes = _latest_existing_mtime([path for path in source_paths if path is not None])
        pointer_time = _parse_datetime(excel_pointer.get("committed_at") or excel_pointer.get("created_at"))
        source_ready = max([value for value in [source_mtimes, pointer_time] if value is not None], default=None)
        if source_ready:
            return source_ready, "active_excel_lakehouse_dataset", str(excel_pointer.get("dataset_id") or "")

    pointer_path = base_dir / "outputs" / "reports" / "active_dataset_pointer.json"
    pointer = _read_json(pointer_path)
    if pointer and pointer.get("status") == "committed":
        source_paths = [
            pointer.get("active_excel"),
        ]
        source_mtimes = _latest_existing_mtime([path for path in (_resolve_path(base_dir, item) for item in source_paths) if path is not None])
        pointer_time = _parse_datetime(pointer.get("committed_at") or pointer.get("created_at"))
        source_ready = max([value for value in [source_mtimes, pointer_time] if value is not None], default=None)
        if source_ready:
            return source_ready, "active_dataset_pointer", str(pointer.get("session_id") or "")
    return config_source_event.astimezone(timezone.utc), "runtime_config.source_event", None


def _gold_ready_time(base_dir: Path, active_session_id: str | None) -> tuple[datetime | None, str]:
    metadata = _read_json(base_dir / "data" / "generated" / "excel_lakehouse_metadata.json")
    if active_session_id and metadata and metadata.get("dataset_id") and metadata.get("dataset_id") != active_session_id:
        return None, "Gold Excel tersedia, tetapi bukan untuk dataset aktif."
    artifacts = [base_dir / path for path in CORE_GOLD_ARTIFACTS]
    if not all(path.exists() for path in artifacts):
        return None, "Gold Excel belum lengkap; latency berjalan dihitung sampai waktu saat ini."
    return _latest_existing_mtime(artifacts), "Gold Excel artifacts lengkap."


def compute_pipeline_latency(base_dir: Path | str | None = None, write_output: bool = True) -> dict[str, Any]:
    base = Path(base_dir) if base_dir is not None else ROOT_DIR
    pointer = _read_json(base / "outputs" / "reports" / "active_excel_lakehouse_dataset.json") or {}
    session_id = str(pointer.get("dataset_session_id") or pointer.get("dataset_id") or "")
    manifests = base / "outputs" / "reports" / "pipeline_runs"
    candidates = sorted(manifests.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True) if manifests.exists() else []
    manifest = next((_read_json(path) for path in candidates if (_read_json(path) or {}).get("dataset_session_id") == session_id), {}) or {}
    required = ["dataset_session_id", "pipeline_run_id", "upload_committed_at", "gold_finished_at"]
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        result = {"status": "not_available", "dataset_session_id": session_id or None, "missing_fields": missing, "message": "Pipeline latency tidak dihitung tanpa manifest run terkorolasi."}
    else:
        t0 = _parse_datetime(manifest["upload_committed_at"]); t1 = _parse_datetime(manifest["gold_finished_at"])
        if t0 is None or t1 is None or t1 < t0:
            result = {"status": "invalid_timeline", "dataset_session_id": session_id, "message": "Timeline run tidak valid."}
        else:
            result = {"status": "validated", "dataset_session_id": session_id, "pipeline_run_id": manifest["pipeline_run_id"], "upload_committed_at": t0.isoformat(), "gold_finished_at": t1.isoformat(), "pipeline_latency_seconds": (t1-t0).total_seconds(), "latency_seconds": (t1-t0).total_seconds()}
    if write_output:
        output_dir = base / "outputs" / "metrics" if base_dir is not None else OUTPUTS_DIR / "metrics"
        write_json(output_dir / "pipeline_latency.json", result)
    return result


def main() -> None:
    print(compute_pipeline_latency(write_output=True))


if __name__ == "__main__":
    main()
