from __future__ import annotations

import subprocess
import sys
from typing import Any

from .activity import append_activity
from .metrics import metrics_payload
from .paths import ROOT_DIR


COMMANDS: dict[str, list[list[str]]] = {
    "generate-data": [[sys.executable, "src/generators/generate_all.py"]],
    "quality-gate": [[sys.executable, "src/validation/quality_gate.py"]],
    "bronze": [[sys.executable, "src/transformations/bronze_ingest.py"]],
    "silver": [[sys.executable, "src/transformations/silver_clean.py"]],
    "gold": [[sys.executable, "src/transformations/gold_star_schema.py"]],
    "metrics": [
        [sys.executable, "src/metrics/reconcile_control_total.py"],
        [sys.executable, "src/metrics/pipeline_latency.py"],
        [sys.executable, "src/metrics/data_freshness.py"],
        [sys.executable, "src/metrics/dropout_rate.py"],
        [sys.executable, "src/metrics/data_quality_score.py"],
        [sys.executable, "src/metrics/generate_uat.py"],
    ],
    "validate-gold": [[sys.executable, "src/metrics/reconcile_control_total.py"]],
}

FULL_RUN_BASIC = ["generate-data", "quality-gate", "bronze", "silver", "gold", "metrics"]
ACTIVITY_ACTIONS = {
    "generate-data": ("generate_data", "raw"),
    "quality-gate": ("quality_gate_process", "quality_gate"),
    "bronze": ("extract_bronze", "bronze"),
    "silver": ("clean_silver", "silver"),
    "gold": ("load_gold_schema", "gold"),
    "metrics": ("metrics", "outputs/metrics"),
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
    for args in commands:
        try:
            completed = subprocess.run(
                args,
                cwd=ROOT_DIR,
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


def run_full(mode: str = "local-basic") -> dict[str, Any]:
    if mode != "local-basic":
        append_activity("full-run", "pipeline", "failed", f"Mode belum tersedia: {mode}", "local scripts")
        return {"status": "failed", "message": "Mode full-docker belum diaktifkan pada backend lokal awal.", "mode": mode, "steps": []}

    results = []
    status = "success"
    for name in [*FULL_RUN_BASIC, "validate-gold"]:
        result = run_command_group(name, timeout=900)
        results.append(result)
        if result["status"] != "success":
            status = "failed"
            break
    append_activity("full-run", "pipeline", status, f"Full run {mode} {status}.", "local scripts")
    return {"status": status, "mode": mode, "steps": results, "metrics": metrics_payload()}
