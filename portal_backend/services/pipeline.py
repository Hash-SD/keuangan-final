from __future__ import annotations

import subprocess
import sys
import os
from typing import Any

from .activity import append_activity
from .metrics import metrics_payload
from .paths import ROOT_DIR
from src.common.runtime_paths import active_dataset_pointer


COMMANDS: dict[str, list[list[str]]] = {
    "excel-lakehouse": [[sys.executable, "src/transformations/excel_lakehouse_pipeline.py"]],
    "bronze": [[sys.executable, "src/transformations/excel_lakehouse_pipeline.py"]],
    "silver": [[sys.executable, "src/transformations/excel_lakehouse_pipeline.py"]],
    "gold": [[sys.executable, "src/transformations/excel_lakehouse_pipeline.py"]],
    "load-gold-postgres": [[sys.executable, "src/sql/load_gold_to_postgres.py"]],
    "superset-excel": [[sys.executable, "src/sql/setup_superset_excel_assets.py"]],
    "metrics": [
        [sys.executable, "src/metrics/pipeline_latency.py"],
        [sys.executable, "src/metrics/data_freshness.py"],
        [sys.executable, "src/metrics/generate_uat.py"],
        [sys.executable, "src/storage/excel_storage_manifest.py"],
        [sys.executable, "src/status/system_truth_status.py"],
    ],
    "excel-storage-manifest": [[sys.executable, "src/storage/excel_storage_manifest.py"]],
    "excel-count-validation": [[sys.executable, "src/metrics/validate_excel_lakehouse_counts.py"]],
    "quality-gate": [[sys.executable, "src/metrics/validate_excel_lakehouse_counts.py"]],
    "truth-status": [[sys.executable, "src/status/system_truth_status.py"]],
    "validate-gold": [[sys.executable, "src/metrics/validate_excel_lakehouse_counts.py"]],
}

FULL_RUN_BASIC = [
    "excel-lakehouse",
    "excel-count-validation",
    "excel-storage-manifest",
    "load-gold-postgres",
    "superset-excel",
    "truth-status",
]
FULL_RUN_UPLOADED_SOURCES = FULL_RUN_BASIC
ACTIVITY_ACTIONS = {
    "quality-gate": ("excel_count_validation", "outputs/reports"),
    "bronze": ("excel_lakehouse", "bronze"),
    "silver": ("excel_lakehouse", "silver"),
    "gold": ("excel_lakehouse", "gold"),
    "excel-lakehouse": ("excel_lakehouse", "gold/fact_anggaran"),
    "load-gold-postgres": ("load_gold_to_postgres", "postgres/gold"),
    "superset-excel": ("superset_excel_dashboard", "superset"),
    "metrics": ("metrics", "outputs/metrics"),
    "excel-storage-manifest": ("excel_storage_manifest", "outputs/reports"),
    "excel-count-validation": ("excel_count_validation", "outputs/reports"),
    "truth-status": ("system_truth_status", "outputs/reports"),
    "validate-gold": ("validate_mart", "gold"),
}


def _tail(text: str, limit: int = 4000) -> str:
    return text[-limit:] if len(text) > limit else text


def run_command_group(name: str, timeout: int = 600) -> dict[str, Any]:
    commands = COMMANDS.get(name)
    if commands is None:
        return {"status": "failed", "message": f"Command tidak dikenal: {name}", "steps": []}

    steps = []
    status = "success"
    env = {**os.environ, "DATASET_MODE": "uploaded_excel"}
    for args in commands:
        try:
            completed = subprocess.run(
                args,
                cwd=ROOT_DIR,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            step = {
                "args": args,
                "returncode": completed.returncode,
                "stdout": _tail(completed.stdout),
                "stderr": _tail(completed.stderr),
                "status": "success" if completed.returncode == 0 else "failed",
            }
        except subprocess.TimeoutExpired as exc:
            step = {
                "args": args,
                "returncode": None,
                "stdout": _tail(exc.stdout or ""),
                "stderr": _tail(exc.stderr or ""),
                "status": "failed",
                "message": f"Timeout setelah {timeout} detik.",
            }
        steps.append(step)
        if step["status"] != "success":
            status = "failed"
            break

    activity_action, activity_source = ACTIVITY_ACTIONS.get(name, (name, "pipeline"))
    append_activity(
        action=activity_action,
        source=activity_source,
        status=status,
        target="local scripts",
        message=f"Pipeline step {name} {status}.",
    )
    response = {"status": status, "command": name, "steps": steps}
    if name in {"quality-gate", "metrics", "validate-gold"}:
        response["metrics"] = metrics_payload()
    return response


def _has_active_uploaded_sources() -> bool:
    return bool(active_dataset_pointer())


def _full_run_steps() -> list[str]:
    return FULL_RUN_UPLOADED_SOURCES


def run_full(mode: str = "local-basic") -> dict[str, Any]:
    if mode != "local-basic":
        append_activity("full-run", "pipeline", "failed", f"Mode belum tersedia: {mode}", "local scripts")
        return {"status": "failed", "message": "Mode full-docker belum diaktifkan pada backend lokal awal.", "mode": mode, "steps": []}

    results = []
    status = "success"
    steps = _full_run_steps()
    for name in [*steps, "validate-gold"]:
        result = run_command_group(name, timeout=900)
        results.append(result)
        if result["status"] != "success":
            status = "failed"
            break
    append_activity("full-run", "pipeline", status, f"Full run {mode} {status}.", "local scripts")
    return {
        "status": status,
        "mode": mode,
        "source_mode": "uploaded_excel",
        "steps": results,
        "metrics": metrics_payload(),
    }
