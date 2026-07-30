from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR


def _parse(value: object) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def compute_freshness(manifest: dict[str, Any]) -> dict[str, Any]:
    required = ["dataset_session_id", "pipeline_run_id", "upload_committed_at", "gold_finished_at", "dashboard_verified_at"]
    missing = [key for key in required if not manifest.get(key)]
    if missing:
        return {"status": "not_available", "missing_fields": missing, "message": "Freshness tidak dihitung karena timeline run belum lengkap."}
    t0, t1, t2 = (_parse(manifest[key]) for key in ("upload_committed_at", "gold_finished_at", "dashboard_verified_at"))
    if not t0 <= t1 <= t2:
        return {"status": "invalid_timeline", "message": "Urutan T0 <= T1 <= T2 tidak terpenuhi."}
    return {"status": "validated", "dataset_session_id": manifest["dataset_session_id"], "pipeline_run_id": manifest["pipeline_run_id"], "upload_committed_at": t0.isoformat(), "gold_finished_at": t1.isoformat(), "dashboard_verified_at": t2.isoformat(), "pipeline_latency_seconds": (t1-t0).total_seconds(), "dashboard_serving_delay_seconds": (t2-t1).total_seconds(), "freshness_seconds": (t2-t0).total_seconds()}


def main() -> None:
    manifests = sorted((OUTPUTS_DIR / "reports" / "pipeline_runs").glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    manifest = json.loads(manifests[0].read_text(encoding="utf-8")) if manifests else {}
    write_json(OUTPUTS_DIR / "metrics" / "data_freshness.json", compute_freshness(manifest))


if __name__ == "__main__":
    main()
