from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "outputs" / "reports"


def _json(name: str) -> dict:
    path = REPORTS / name
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> None:
    cleanup = _json("cleanup_report.json")
    test = _json("test_report.json")
    health = _json("service_health_report.json")
    smoke = _json("release_fixture_smoke.json")
    errors = []
    if cleanup.get("status") != "CLEAN": errors.append("runtime_workspace_not_clean")
    if test.get("status") != "PASSED": errors.append("mandatory_tests_not_passed")
    if smoke.get("status") != "PASSED": errors.append("postgres_superset_fixture_smoke_not_passed")
    required = ("portal", "airflow", "postgresql", "minio", "trino", "superset")
    services = health.get("services") or {}
    for name in required:
        if services.get(name) != "HEALTHY": errors.append(f"service_not_healthy:{name}")
    active_paths = [ROOT / "outputs/reports/active_excel_lakehouse_dataset.json", ROOT / "outputs/reports/active_gold_run.json"]
    if any(path.exists() for path in active_paths): errors.append("active_runtime_artifact_present")
    decision = "READY_FOR_USER_UPLOAD" if not errors else "NOT_READY_FOR_USER_UPLOAD"
    gate = {"decision": decision, "status": decision, "tests": test.get("status", "NOT_RUN"), "runtime_workspace": cleanup.get("status", "NOT_CLEAN"), "services": services, "fixture_smoke": smoke.get("status", "NOT_RUN"), "blocking_errors": errors, "warnings": [], "checked_at": datetime.now(timezone.utc).isoformat(), "python": sys.version, "git": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()}
    (REPORTS / "production_release_gate.json").write_text(json.dumps(gate, indent=2), encoding="utf-8")
    (REPORTS / "production_release_gate.md").write_text("# Production Release Gate\n\nKeputusan akhir: **" + decision + "**\n\n```json\n" + json.dumps(gate, indent=2) + "\n```\n", encoding="utf-8")
    print(json.dumps(gate))


if __name__ == "__main__":
    main()
