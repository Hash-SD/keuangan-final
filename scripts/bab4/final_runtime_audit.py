"""Collect runtime evidence for Bab IV 4.2 without manufacturing results.

The collector is intentionally fail-closed. It may report an unavailable
canonical run, but it never promotes an old run merely because its row count
looks similar to the active dataset.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_BASE = ROOT / "outputs" / "bab4_evidence_final"
OUTPUT = OUTPUT_BASE
TRANSCRIPTS = OUTPUT / "command_transcripts"
RAW_LOGS = OUTPUT / "raw_logs"
sys.path.insert(0, str(ROOT))

from src.validation.dataset_contract import validate_active_dataset_file


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or sorted({key for row in rows for key in row}) or ["status"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if re.search(r"pass|secret|token|cookie|key", key, re.I) else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def redact_text(value: str) -> str:
    return re.sub(r"(?i)([A-Z0-9_]*(?:PASSWORD|SECRET|TOKEN|ACCESS_KEY|API_KEY)[A-Z0-9_]*)=([^\\s\\\"]+)", r"\1=[REDACTED]", value)


def run_command(name: str, args: list[str], *, container: str | None = None, timeout: int = 60) -> dict[str, Any]:
    started = now()
    completed = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout, check=False)
    finished = now()
    result = {
        "name": name,
        "command": " ".join(args),
        "container": container,
        "started_at": started,
        "finished_at": finished,
        "exit_code": completed.returncode,
        "stdout": redact_text(completed.stdout),
        "stderr": redact_text(completed.stderr),
    }
    write_json(TRANSCRIPTS / f"{len(list(TRANSCRIPTS.glob('*.json'))):04d}_{name}.json", result)
    (RAW_LOGS / f"{name}.stdout.log").write_text(redact_text(completed.stdout), encoding="utf-8")
    (RAW_LOGS / f"{name}.stderr.log").write_text(redact_text(completed.stderr), encoding="utf-8")
    return result


def http_probe(name: str, url: str) -> dict[str, Any]:
    started = now()
    try:
        with urlopen(Request(url, method="GET"), timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace")
            result = {"name": name, "url": url, "status": "PASS", "http_status": response.status, "body": body, "checked_at": started}
    except Exception as exc:
        result = {"name": name, "url": url, "status": "FAIL", "http_status": None, "body": "", "error": str(exc), "checked_at": started}
    write_json(RAW_LOGS / f"http_{name}.json", result)
    return result


def collect_inventory() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    services_result = run_command("compose_services", ["docker", "compose", "config", "--services"])
    services = [line.strip() for line in services_result["stdout"].splitlines() if line.strip()]
    ps_result = run_command("compose_ps", ["docker", "compose", "ps", "--format", "json"])
    containers: list[dict[str, Any]] = []
    for line in ps_result["stdout"].splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        container_name = item.get("Name") or item.get("Names")
        if not container_name:
            continue
        inspect = run_command(f"inspect_{container_name}", ["docker", "inspect", container_name], container=container_name)
        inspect_payload: list[Any] = []
        try:
            inspect_payload = json.loads(inspect["stdout"])
        except json.JSONDecodeError:
            pass
        state = inspect_payload[0].get("State", {}) if inspect_payload else {}
        config = inspect_payload[0].get("Config", {}) if inspect_payload else {}
        containers.append({
            "service": item.get("Service"),
            "container_name": container_name,
            "container_id": item.get("ID"),
            "image": item.get("Image"),
            "state": state.get("Status") or item.get("State"),
            "health": (state.get("Health") or {}).get("Status"),
            "started_at": state.get("StartedAt"),
            "restart_count": (inspect_payload[0].get("RestartCount") if inspect_payload else None),
            "ports": item.get("Ports"),
            "networks": list((inspect_payload[0].get("NetworkSettings", {}).get("Networks", {}) if inspect_payload else {}).keys()),
            "mounts": [mount.get("Destination") for mount in (inspect_payload[0].get("Mounts", []) if inspect_payload else [])],
            "environment": redact(config.get("Env", [])),
        })
        run_command(f"logs_{container_name}", ["docker", "logs", "--timestamps", "--tail", "500", container_name], container=container_name)
    write_csv(OUTPUT / "02_implementasi" / "421_lingkungan_dan_orkestrasi" / "container_health.csv", containers)
    write_csv(OUTPUT / "00_manifest" / "compose_services.csv", [{"service": service} for service in services], ["service"])
    write_csv(OUTPUT / "00_manifest" / "container_inventory.csv", containers)
    return containers, [{"service": service} for service in services]


def collect_canonical() -> dict[str, Any]:
    pointer_path = ROOT / "outputs" / "reports" / "active_excel_lakehouse_dataset.json"
    validation = validate_active_dataset_file(pointer_path, ROOT) if pointer_path.exists() else {"valid": False, "errors": ["active dataset pointer tidak ditemukan"]}
    payload: dict[str, Any] = {}
    if pointer_path.exists():
        try:
            payload = json.loads(pointer_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
    manifest = {
        "status": "VALID" if validation.get("valid") else "NOT_READY",
        "dataset_session_id": validation.get("dataset_session_id"),
        "pipeline_run_id": None,
        "airflow_dag_run_id": None,
        "upload_committed_at": payload.get("upload_committed_at"),
        "pipeline_started_at": None,
        "gold_finished_at": None,
        "postgres_loaded_at": None,
        "superset_refresh_finished_at": None,
        "dashboard_verified_at": None,
        "validation": validation,
        "selection_rule": "Tidak memilih run lama tanpa kecocokan identitas dan file sumber.",
    }
    write_json(OUTPUT / "00_manifest" / "canonical_run_manifest.json", manifest)
    write_csv(OUTPUT / "00_manifest" / "canonical_run_manifest.csv", [manifest])
    write_json(OUTPUT / "00_manifest" / "reproducibility.json", {
        "collected_at": now(),
        "git_commit": run_command("git_commit", ["git", "rev-parse", "HEAD"])["stdout"].strip(),
        "git_branch": run_command("git_branch", ["git", "branch", "--show-current"])["stdout"].strip(),
        "python_version": run_command("python_version", [sys.executable, "--version"])["stdout"].strip() or run_command("python_version_stderr", [sys.executable, "--version"])["stderr"].strip(),
        "docker_version": run_command("docker_version", ["docker", "version", "--format", "{{.Server.Version}}"])["stdout"].strip(),
        "compose_version": run_command("compose_version", ["docker", "compose", "version"])["stdout"].strip(),
        "host_os": os.name,
    })
    return manifest


def collect_airflow(manifest: dict[str, Any]) -> None:
    base = OUTPUT / "02_implementasi" / "421_lingkungan_dan_orkestrasi"
    base.mkdir(parents=True, exist_ok=True)
    dag = "keuangan_prodi_excel_lakehouse_dag"
    runs = run_command("airflow_dag_runs", ["docker", "exec", "keuangan-airflow-webserver", "airflow", "dags", "list-runs", "-d", dag, "-o", "json"], container="keuangan-airflow-webserver")
    tasks = run_command("airflow_task_types", ["docker", "exec", "keuangan-airflow-webserver", "airflow", "tasks", "list", dag, "-o", "json"], container="keuangan-airflow-webserver")
    (base / "airflow_dag_runs.raw.json").write_text(runs["stdout"], encoding="utf-8")
    (base / "airflow_task_types.raw.json").write_text(tasks["stdout"], encoding="utf-8")
    write_json(base / "airflow_canonical_run.json", {"status": "NOT_READY", "reason": "Canonical dataset invalid; no Airflow run promoted."})
    write_json(base / "service_health.json", {"airflow_cli": runs["exit_code"] == 0, "dag_id": dag, "canonical_run": "NOT_READY"})


def collect_database_and_storage(manifest: dict[str, Any]) -> None:
    base = OUTPUT / "02_implementasi" / "423_gold_dan_dashboard"
    base.mkdir(parents=True, exist_ok=True)
    queries = {
        "postgres_fact_validation": "SELECT COUNT(*) AS row_count, COUNT(DISTINCT item_id) AS unique_items, COALESCE(SUM(jumlah_weighted_iku),0) AS weighted_total FROM gold.fact_anggaran;",
        "postgres_schema": "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='gold' ORDER BY table_name;",
    }
    postgres_rows = []
    for name, sql in queries.items():
        result = run_command(name, ["docker", "exec", "keuangan-postgres-metastore", "psql", "-U", "lakehouse", "-d", "metastore", "-P", "footer=off", "-A", "-F", ",", "-c", sql], container="keuangan-postgres-metastore")
        (base / f"{name}.txt").write_text(result["stdout"] + result["stderr"], encoding="utf-8")
        postgres_rows.append({"query": name, "exit_code": result["exit_code"], "output": result["stdout"].strip()})
    write_csv(base / "postgres_fact_validation.csv", postgres_rows)
    trino = run_command("trino_catalogs", ["docker", "exec", "keuangan-trino", "trino", "--execute", "SHOW CATALOGS"], container="keuangan-trino")
    (base / "trino_catalogs.txt").write_text(trino["stdout"] + trino["stderr"], encoding="utf-8")
    write_json(base / "iceberg_validation.json", {"status": "CONFIGURED_ONLY", "reason": "Catalog configuration exists; operational table/snapshot evidence is absent."})
    write_json(base / "minio_validation.json", {"status": "NOT_VERIFIED", "reason": "Object listing is collected only for actual canonical run."})


def collect_portal() -> None:
    base = OUTPUT / "02_implementasi" / "421_lingkungan_dan_orkestrasi"
    base.mkdir(parents=True, exist_ok=True)
    paths = ["/api/health", "/api/readiness", "/api/excel-lakehouse/status", "/api/system-truth/status", "/api/superset/status", "/api/superset/assets", "/api/data/preview", "/api/metrics"]
    results = [http_probe(path.strip("/").replace("/", "_"), f"http://localhost:8091{path}") for path in paths]
    write_csv(base / "portal_endpoint_validation.csv", results)
    write_json(base / "portal_validation.json", {"checked_at": now(), "endpoints": results})


def finalize(manifest: dict[str, Any], containers: list[dict[str, Any]]) -> None:
    readiness = {
        "section_42_1": "READY" if containers else "NOT_READY",
        "section_42_2": "NOT_READY",
        "section_42_3": "READY_WITH_LIMITATIONS" if manifest["status"] == "VALID" else "NOT_READY",
        "overall_decision": "NOT_READY_FOR_FINAL_WRITING",
        "canonical_run": manifest,
        "limitations": manifest["validation"].get("errors", []),
        "iceberg": "CONFIGURED_ONLY",
        "generated_at": now(),
    }
    final = OUTPUT / "final_validation"
    write_json(final / "section_42_readiness.json", readiness)
    (final / "section_42_readiness.md").write_text(
        "# Section 4.2 Readiness\n\n"
        f"- 4.2.1: **{readiness['section_42_1']}**\n"
        f"- 4.2.2: **{readiness['section_42_2']}**\n"
        f"- 4.2.3: **{readiness['section_42_3']}**\n"
        f"- Decision: **{readiness['overall_decision']}**\n\n"
        "Evidence is fail-closed; unavailable values are not substituted.\n",
        encoding="utf-8",
    )
    write_csv(final / "section_42_claim_registry.csv", [
        {"claim": "canonical dataset", "status": manifest["status"], "evidence": "00_manifest/canonical_run_manifest.json"},
        {"claim": "Iceberg operational", "status": "CONFIGURED_ONLY", "evidence": "02_implementasi/423_gold_dan_dashboard/iceberg_validation.json"},
    ])
    write_csv(final / "section_42_evidence_map.csv", [
        {"subsection": "4.2.1", "status": readiness["section_42_1"], "evidence": "02_implementasi/421_lingkungan_dan_orkestrasi"},
        {"subsection": "4.2.2", "status": readiness["section_42_2"], "evidence": "02_implementasi/422_bronze_dan_silver"},
        {"subsection": "4.2.3", "status": readiness["section_42_3"], "evidence": "02_implementasi/423_gold_dan_dashboard"},
    ])
    (final / "section_42_limitations.md").write_text("# Limitations\n\n" + "\n".join(f"- {item}" for item in readiness["limitations"]) + "\n", encoding="utf-8")
    artifacts = []
    for path in OUTPUT.rglob("*"):
        if path.is_file() and path.name != "artifact_manifest.csv":
            artifacts.append({"path": path.relative_to(OUTPUT).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(OUTPUT / "00_manifest" / "artifact_manifest.csv", artifacts, ["path", "size_bytes", "sha256"])


def main() -> None:
    global OUTPUT, TRANSCRIPTS, RAW_LOGS
    evidence_run_id = datetime.now(timezone.utc).strftime("audit_%Y%m%dT%H%M%SZ")
    OUTPUT = OUTPUT_BASE / evidence_run_id
    TRANSCRIPTS = OUTPUT / "command_transcripts"
    RAW_LOGS = OUTPUT / "raw_logs"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    RAW_LOGS.mkdir(parents=True, exist_ok=True)
    containers, _ = collect_inventory()
    manifest = collect_canonical()
    collect_airflow(manifest)
    collect_database_and_storage(manifest)
    collect_portal()
    finalize(manifest, containers)
    print(json.dumps({"output": str(OUTPUT), "canonical_status": manifest["status"], "decision": "NOT_READY_FOR_FINAL_WRITING"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
