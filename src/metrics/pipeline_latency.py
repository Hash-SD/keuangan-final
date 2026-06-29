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
    config = get_runtime_config()
    source_ready, source_basis, session_id = _active_source_ready_time(base, config.source_event)
    gold_ready, gold_message = _gold_ready_time(base, session_id)
    computed_at = datetime.now(timezone.utc)
    end_time = gold_ready or computed_at
    seconds = max(int((end_time - source_ready).total_seconds()), 0)
    status = "validated" if gold_ready else "running"
    result = {
        "batch_id": config.batch_id,
        "target_prodi": config.target_prodi,
        "target_tahun_akademik": config.target_tahun_akademik,
        "target_label": config.target_label,
        "source_arrival": source_ready.isoformat(),
        "source_basis": source_basis,
        "dataset_session_id": session_id,
        "gold_ready": gold_ready.isoformat() if gold_ready else None,
        "computed_at": computed_at.isoformat(),
        "latency_seconds": seconds,
        "pipeline_latency_seconds": seconds,
        "elapsed_seconds": seconds,
        "status": status,
        "message": "Latency dihitung realtime dari sumber aktif ke Gold terbaru." if gold_ready else gold_message,
    }
    if write_output:
        output_dir = base / "outputs" / "metrics" if base_dir is not None else OUTPUTS_DIR / "metrics"
        write_json(output_dir / "pipeline_latency.json", result)
    return result


def main() -> None:
    print(compute_pipeline_latency(write_output=True))


if __name__ == "__main__":
    main()
