from __future__ import annotations

from typing import Any

from .files import read_json
from .paths import OUTPUTS_DIR


def production_readiness() -> dict[str, Any]:
    """Fail closed unless a current release gate explicitly authorizes upload."""
    gate = read_json(OUTPUTS_DIR / "reports" / "production_release_gate.json") or {}
    ready = gate.get("decision") == "READY_FOR_USER_UPLOAD"
    errors = list(gate.get("blocking_errors") or [])
    if not ready and not errors:
        errors.append("production_release_gate_missing_or_not_ready")
    services = gate.get("services") or {name: "UNKNOWN" for name in ("portal", "airflow", "postgresql", "minio", "trino", "superset")}
    return {
        "status": "READY_FOR_USER_UPLOAD" if ready else "NOT_READY_FOR_USER_UPLOAD",
        "tests": gate.get("tests", "NOT_RUN"),
        "runtime_workspace": gate.get("runtime_workspace", "NOT_CLEAN"),
        "active_dataset": None,
        "active_pipeline_run": None,
        "services": services,
        "blocking_errors": errors,
        "warnings": list(gate.get("warnings") or []),
    }
