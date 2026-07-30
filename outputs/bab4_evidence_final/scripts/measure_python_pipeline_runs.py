"""Measure five end-to-end Python pipeline executions against the active RAB bundle."""
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "bab4_evidence_final" / "03_pengujian" / "432_kinerja_dashboard"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for ordinal in range(1, 6):
        started = datetime.now(timezone.utc)
        tick = time.perf_counter()
        completed = subprocess.run([sys.executable, "src/transformations/excel_lakehouse_pipeline.py"], cwd=ROOT, capture_output=True, text=True, timeout=180)
        duration = time.perf_counter() - tick
        metadata_path = ROOT / "data/generated/excel_lakehouse_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
        rows.append({"run_ordinal": ordinal, "measurement_type": "Waktu Eksekusi Pipeline Python End-to-End", "started_at": started.isoformat(), "ended_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": round(duration, 3), "exit_code": completed.returncode, "pipeline_run_id": metadata.get("run_id"), "dataset_session_id": metadata.get("dataset_session_id"), "bronze_cells": metadata.get("bronze_cells"), "silver_rab_items": metadata.get("silver_rab_items"), "gold_rows": metadata.get("fact_anggaran_rows"), "stdout_tail": completed.stdout[-500:], "stderr_tail": completed.stderr[-500:], "status": "PASS" if completed.returncode == 0 else "FAILED"})
    frame = pd.DataFrame(rows)
    frame.to_csv(OUT / "python_pipeline_latency_runs.csv", index=False, encoding="utf-8-sig")
    stats = frame["duration_seconds"].describe().to_dict()
    (OUT / "python_pipeline_latency_statistics.json").write_text(json.dumps({"measurement_type": "Waktu Eksekusi Pipeline Python End-to-End", "run_count": len(frame), "all_pass": bool(frame["status"].eq("PASS").all()), "statistics_seconds": stats}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"runs": len(frame), "pass": int(frame["status"].eq("PASS").sum()), "durations": frame["duration_seconds"].tolist()}, ensure_ascii=False))
    return 0 if frame["status"].eq("PASS").all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
