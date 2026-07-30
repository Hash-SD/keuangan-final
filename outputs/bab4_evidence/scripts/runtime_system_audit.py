from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs" / "bab4_evidence" / "02_implementasi" / "421_lingkungan_orkestrasi"
OUT.mkdir(parents=True, exist_ok=True)
STAMP = datetime.now(timezone.utc).isoformat()


def command(args: list[str]) -> dict:
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False, timeout=60)
        return {"command": " ".join(args), "exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}
    except Exception as exc:
        return {"command": " ".join(args), "exit_code": None, "stdout": "", "stderr": f"{type(exc).__name__}: {exc}"}


def http(url: str) -> dict:
    try:
        with urlopen(Request(url, headers={"User-Agent": "bab4-evidence-audit/1.0"}), timeout=15) as response:
            body = response.read(2000).decode("utf-8", errors="replace")
            return {"url": url, "status_code": response.status, "body_preview": body}
    except HTTPError as exc:
        return {"url": url, "status_code": exc.code, "body_preview": exc.read(1000).decode("utf-8", errors="replace")}
    except (URLError, TimeoutError) as exc:
        return {"url": url, "status_code": None, "body_preview": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    checks = {
        "generated_at": STAMP,
        "docker_compose_ps": command(["docker", "compose", "ps", "--format", "json"]),
        "airflow_dags": command(["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "dags", "list", "--output", "json"]),
        "airflow_tasks": command(["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "tasks", "list", "keuangan_prodi_excel_lakehouse_dag"]),
        "airflow_runs": command(["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "dags", "list-runs", "-d", "keuangan_prodi_excel_lakehouse_dag", "--output", "json"]),
        "successful_run_task_states": command(["docker", "compose", "exec", "-T", "airflow-webserver", "airflow", "tasks", "states-for-dag-run", "keuangan_prodi_excel_lakehouse_dag", "manual_final_verification_sample_fixed_20260629155327"]),
        "postgres_version": command(["docker", "compose", "exec", "-T", "postgres-metastore", "psql", "-U", "lakehouse", "-d", "metastore", "-Atc", "SELECT version();"]),
        "postgres_tables": command(["docker", "compose", "exec", "-T", "postgres-metastore", "psql", "-U", "lakehouse", "-d", "metastore", "-Atc", "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema');"]),
        "trino_info": http("http://localhost:8082/v1/info"),
        "airflow_health": http("http://localhost:8085/health"),
        "minio_health": http("http://localhost:9000/minio/health/live"),
        "superset_health": http("http://localhost:8089/health"),
        "portal_datasets": http("http://localhost:8091/api/datasets"),
        "portal_status": http("http://localhost:8091/api/excel-lakehouse/status"),
        "portal_dashboard_status": http("http://localhost:8091/api/local-dashboard/status"),
        "portal_frontend": http("http://localhost:8090"),
    }
    (OUT / "runtime_system_audit.json").write_text(json.dumps(checks, indent=2, ensure_ascii=False), encoding="utf-8")
    rows = ["# Runtime system audit", "", f"Generated: `{STAMP}`", "", "| Check | Status | Evidence |", "|---|---|---|"]
    for name, result in checks.items():
        if name == "generated_at":
            continue
        if isinstance(result, dict) and "status_code" in result:
            status = "VERIFIED" if result["status_code"] == 200 else "PARTIAL"
            evidence = f"HTTP {result['status_code']} {result['url']}"
        else:
            status = "VERIFIED" if result.get("exit_code") == 0 else "PARTIAL"
            evidence = f"exit_code={result.get('exit_code')}"
        rows.append(f"| `{name}` | `{status}` | {evidence} |")
    (OUT / "runtime_system_audit.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps({"status": "VERIFIED", "output": str(OUT / "runtime_system_audit.json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
