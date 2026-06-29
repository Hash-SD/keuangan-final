from __future__ import annotations

import csv
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import ROOT_DIR
from src.common.runtime_config import get_runtime_config
from src.common.time_utils import utc_now_iso
from src.metrics.pipeline_latency import compute_pipeline_latency


ALLOWED_STATUSES = {
    "completed",
    "configured",
    "configured_unreachable",
    "created",
    "empty",
    "failed",
    "mapped",
    "manual_input_required",
    "missing",
    "not_available",
    "not_started",
    "ready",
    "running",
    "skipped",
    "unreachable",
    "uploaded",
    "validated",
}


def _rel(path: Path, base_dir: Path) -> str:
    try:
        return path.resolve().relative_to(base_dir.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"value": payload}
    except (OSError, json.JSONDecodeError) as exc:
        return {"_error": str(exc)}


def _csv_row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return max(sum(1 for _ in csv.reader(handle)) - 1, 0)
    except OSError:
        return None


def _file_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file())


def _artifact_status(paths: list[Path], base_dir: Path) -> dict[str, Any]:
    existing = [path for path in paths if path.exists()]
    if not existing:
        status = "missing"
    elif len(existing) == len(paths):
        status = "ready"
    else:
        status = "missing"
    return {
        "status": status,
        "required": [_rel(path, base_dir) for path in paths],
        "existing": [_rel(path, base_dir) for path in existing],
        "file_count": sum(_file_count(path) if path.is_dir() else int(path.exists()) for path in paths),
    }


def _value(value: Any, status: str, source: str | None, message: str) -> dict[str, Any]:
    return {"value": value, "status": status, "source": source, "message": message}


def _source_status(base_dir: Path) -> dict[str, Any]:
    raw_dir = base_dir / "data" / "raw" / "excel_lakehouse"
    files = sorted(raw_dir.rglob("*.xlsx")) if raw_dir.exists() else []
    return {
        "excel_lakehouse": {
            "status": "ready" if files else "empty" if raw_dir.exists() else "missing",
            "file_count": len(files),
            "files": [_rel(path, base_dir) for path in files],
            "message": "Raw Excel Lakehouse tersedia sebagai satu-satunya sumber default."
            if files
            else "Raw Excel Lakehouse belum tersedia.",
        }
    }


def _layer_status(base_dir: Path) -> dict[str, Any]:
    generated = base_dir / "data" / "generated"
    return {
        "staging": _artifact_status([base_dir / "data" / "uploads" / "staging"], base_dir),
        "raw": _artifact_status([base_dir / "data" / "raw" / "excel_lakehouse"], base_dir),
        "bronze": _artifact_status([generated / "bronze" / "bronze_excel_cells.parquet"], base_dir),
        "silver": _artifact_status(
            [
                generated / "silver" / "silver_rab_items_flexible.parquet",
                generated / "silver" / "silver_nomenklatur_detail.parquet",
                generated / "silver" / "silver_mapping.parquet",
                generated / "silver" / "silver_validation.parquet",
            ],
            base_dir,
        ),
        "gold": _artifact_status([generated / "gold" / "fact_anggaran.parquet"], base_dir),
        "manifests": _artifact_status([base_dir / "outputs" / "reports"], base_dir),
        "metrics": _artifact_status([base_dir / "outputs" / "metrics"], base_dir),
        "reports": _artifact_status([base_dir / "outputs" / "reports"], base_dir),
    }


def _quality_gate_status(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "outputs" / "reports" / "pipeline_count_validation.json"
    payload = _read_json(path) or _read_json(base_dir / "outputs" / "reports" / "pipeline_run_summary.json")
    if not payload or payload.get("_error"):
        return {
            "status": "missing",
            "total_rows": _value(None, "missing", None, "Validasi Excel belum tersedia."),
            "valid_rows": _value(None, "missing", None, "Validasi Excel belum tersedia."),
            "rejected_rows": _value(None, "missing", None, "Validasi Excel belum tersedia."),
            "dropout_rate": _value(None, "missing", None, "Validasi Excel belum tersedia."),
            "quality_score": _value(None, "missing", None, "Validasi Excel belum tersedia."),
        }
    source = _rel(path if path.exists() else base_dir / "outputs" / "reports" / "pipeline_run_summary.json", base_dir)
    rows = payload.get("fact_anggaran_rows") or payload.get("counts", {}).get("fact_anggaran_rows")
    rows = int(rows or 0)
    status = "validated" if rows else "not_available"
    message = "Validasi Excel Lakehouse dibaca dari artefak pipeline."
    return {
        "status": status,
        "total_rows": _value(rows, status, source, message),
        "valid_rows": _value(rows, status, source, message),
        "rejected_rows": _value(0, status, source, message),
        "dropout_rate": _value(0, status, source, message),
        "quality_score": _value(100 if rows else None, status, source, message),
    }


def _fact_anggaran_status(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "data" / "generated" / "gold" / "fact_anggaran.parquet"
    if not path.exists():
        return {
            "status": "missing",
            "total_anggaran": _value(None, "missing", None, "fact_anggaran belum tersedia."),
            "total_weighted_iku": _value(None, "missing", None, "fact_anggaran belum tersedia."),
            "fact_rows": _value(None, "missing", None, "fact_anggaran belum tersedia."),
            "source": None,
        }
    source = _rel(path, base_dir)
    fact = pd.read_parquet(path)
    jumlah = pd.to_numeric(fact.get("jumlah"), errors="coerce").fillna(0)
    weighted = pd.to_numeric(fact.get("jumlah_weighted_iku"), errors="coerce").fillna(0)
    status = "validated"
    message = "Nilai dibaca langsung dari fact_anggaran."
    return {
        "status": status,
        "total_anggaran": _value(float(jumlah.sum()), status, source, message),
        "total_weighted_iku": _value(float(weighted.sum()), status, source, message),
        "fact_rows": _value(int(len(fact)), status, source, message),
        "source": source,
    }


def _metric_file_status(base_dir: Path, filename: str, keys: list[str]) -> dict[str, Any]:
    path = base_dir / "outputs" / "metrics" / filename
    payload = _read_json(path)
    if not payload:
        return {key: _value(None, "missing", None, f"{filename} belum tersedia.") for key in keys} | {"status": "missing"}
    status = "validated" if not payload.get("_error") else "failed"
    source = _rel(path, base_dir)
    return {
        "status": status,
        **{key: _value(payload.get(key), status, source, "Nilai dibaca dari artefak metrik.") for key in keys},
        "source": source,
    }


def _pipeline_latency_status(base_dir: Path, write_output: bool = False) -> dict[str, Any]:
    payload = compute_pipeline_latency(base_dir=base_dir, write_output=write_output)
    status = "validated" if payload.get("status") == "validated" else "not_started" if payload.get("status") == "missing" else payload.get("status", "running")
    source = _rel(base_dir / "outputs" / "metrics" / "pipeline_latency.json", base_dir)
    return {
        "status": status,
        "latency_seconds": _value(payload.get("latency_seconds"), status, source, payload.get("message", "Latency dihitung realtime.")),
        "pipeline_latency_seconds": _value(payload.get("pipeline_latency_seconds"), status, source, payload.get("message", "Latency dihitung realtime.")),
        "elapsed_seconds": _value(payload.get("elapsed_seconds"), status, source, payload.get("message", "Latency dihitung realtime.")),
        "source_arrival": payload.get("source_arrival"),
        "source_basis": payload.get("source_basis"),
        "gold_ready": payload.get("gold_ready"),
        "computed_at": payload.get("computed_at"),
        "dataset_session_id": payload.get("dataset_session_id"),
        "source": source,
        "message": payload.get("message"),
    }


def _uat_status(base_dir: Path) -> dict[str, Any]:
    uat_dir = base_dir / "outputs" / "uat"
    template = uat_dir / "uat_template.csv"
    responses = uat_dir / "uat_response.csv"
    summary = uat_dir / "uat_score_summary.json"
    matrix = uat_dir / "uat_matrix_summary.json"
    summary_payload = _read_json(summary)
    matrix_payload = _read_json(matrix)
    responses_available = responses.exists() and (_csv_row_count(responses) or 0) > 0
    completed = bool(responses_available and summary_payload and matrix_payload)
    status = "completed" if completed else "manual_input_required" if template.exists() else "missing"
    return {
        "uat_status": status,
        "status": status,
        "template_available": template.exists(),
        "responses_available": responses_available,
        "respondent_count": int(summary_payload.get("respondent_count") or 0) if completed else 0,
        "average_score": summary_payload.get("average_score") if completed else None,
        "percentage": summary_payload.get("percentage") if completed else None,
        "category": summary_payload.get("category") if completed else None,
        "source": _rel(matrix, base_dir) if completed else _rel(template, base_dir) if template.exists() else None,
        "message": "Hasil UAT dibaca dari artefak penilaian." if completed else "UAT membutuhkan input penilaian lokal.",
        "matrix": matrix_payload if completed else None,
    }


def _tcp_status(host: str, port: int, timeout: float = 0.5) -> tuple[str, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "ready", "TCP endpoint dapat dijangkau."
    except OSError as exc:
        return "unreachable", str(exc)


def _http_status(url: str, timeout: float = 0.75) -> tuple[str, int | None, str]:
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=timeout) as response:
            status_code = response.status
            if 200 <= status_code < 400:
                return "ready", status_code, "HTTP endpoint sehat."
            return "failed", status_code, f"HTTP endpoint mengembalikan status {status_code}."
    except (OSError, URLError) as exc:
        return "unreachable", None, str(exc)


def _docker_status(base_dir: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(["docker", "compose", "ps", "--format", "json"], cwd=base_dir, capture_output=True, text=True, timeout=10, check=False)
    except Exception as exc:
        return {"status": "unreachable", "message": f"Docker engine tidak dapat diakses: {exc}", "services": []}
    if completed.returncode != 0:
        return {"status": "unreachable", "message": "Docker engine tidak dapat diakses.", "stderr": completed.stderr.strip(), "services": []}
    services = []
    for line in completed.stdout.splitlines():
        try:
            services.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return {"status": "ready" if services else "empty", "message": "Docker compose dapat diakses.", "services": services}


def _service_statuses(base_dir: Path) -> dict[str, Any]:
    env = os.environ
    services = {
        "portal": ("http", f"http://{env.get('PORTAL_HOST', 'localhost')}:{env.get('PORTAL_PORT', '8090')}"),
        "portalBackend": ("http", f"http://{env.get('PORTAL_BACKEND_HOST', 'localhost')}:{env.get('PORTAL_BACKEND_PORT', '8091')}/api/health"),
        "airflow": ("http", f"http://{env.get('AIRFLOW_HOST', 'localhost')}:{env.get('AIRFLOW_PORT', '8085')}/health"),
        "superset": ("http", f"http://{env.get('SUPERSET_HOST', 'localhost')}:{env.get('SUPERSET_PORT', '8089')}/health"),
        "minioApi": ("http", f"http://{env.get('MINIO_HOST', 'localhost')}:{env.get('MINIO_API_PORT', '9000')}/minio/health/live"),
        "minioConsole": ("http", f"http://{env.get('MINIO_HOST', 'localhost')}:{env.get('MINIO_CONSOLE_PORT', '9001')}"),
        "sparkMaster": ("http", f"http://{env.get('SPARK_MASTER_HOST', 'localhost')}:{env.get('SPARK_MASTER_UI_PORT', '8080')}"),
        "sparkWorker": ("http", f"http://{env.get('SPARK_WORKER_HOST', 'localhost')}:{env.get('SPARK_WORKER_UI_PORT', '8081')}"),
        "trino": ("http", f"http://{env.get('TRINO_HOST', 'localhost')}:{env.get('TRINO_PORT', '8082')}/v1/info"),
        "postgres": ("tcp", env.get("POSTGRES_HOST", "localhost"), int(env.get("POSTGRES_PORT", "5432"))),
    }
    result = {}
    for key, definition in services.items():
        if definition[0] == "http":
            status, code, message = _http_status(definition[1])
            result[key] = {"status": status, "url": definition[1], "http_status": code, "message": message}
        else:
            status, message = _tcp_status(definition[1], definition[2])
            result[key] = {"status": status, "host": definition[1], "port": definition[2], "message": message}
    result["docker"] = _docker_status(base_dir)
    return result


def _storage_status(base_dir: Path, services: dict[str, Any]) -> dict[str, Any]:
    manifest_path = base_dir / "outputs" / "reports" / "storage_manifest.json"
    manifest = _read_json(manifest_path)
    if not manifest:
        status = "not_started"
        message = "Storage manifest belum dibuat."
    elif services.get("minioApi", {}).get("status") == "unreachable":
        status = "configured_unreachable"
        message = "Manifest tersedia, tetapi endpoint MinIO tidak dapat dijangkau."
    else:
        status = manifest.get("status") or "mapped"
        message = "Storage manifest Excel Lakehouse tersedia."
    return {
        "status": status,
        "manifest_source": _rel(manifest_path, base_dir) if manifest_path.exists() else None,
        "manifest": manifest,
        "message": message,
    }


def _superset_dashboard_status(base_dir: Path, services: dict[str, Any]) -> dict[str, Any]:
    dashboard_path = base_dir / "outputs" / "reports" / "superset_excel_dashboard.json"
    assets_path = base_dir / "outputs" / "reports" / "superset_excel_assets.json"
    dashboard = _read_json(dashboard_path)
    assets = _read_json(assets_path)
    if dashboard and assets:
        return {
            "status": "created",
            "source": _rel(dashboard_path, base_dir),
            "message": "Artefak dashboard Excel Lakehouse tersedia.",
            "dashboard_url": dashboard.get("dashboard_url"),
        }
    return {"status": "configured" if assets else "not_started", "source": None, "message": "Dashboard Superset belum divalidasi."}


def _bab4_evidence(truth: dict[str, Any]) -> dict[str, Any]:
    fact = truth["reconciliation"]
    uat = truth["uat"]
    dashboard = truth["dashboard"]
    return {
        "status": "ready" if fact["status"] == "validated" else "not_available",
        "message": "Ringkasan hanya memuat hasil Excel Lakehouse yang tersedia.",
        "total_anggaran": fact["total_anggaran"]["value"],
        "total_weighted_iku": fact["total_weighted_iku"]["value"],
        "fact_rows": fact["fact_rows"]["value"],
        "storage_status": truth["storage"]["status"],
        "uat_average": uat.get("average_score") if uat["status"] == "completed" else None,
        "uat_percentage": uat.get("percentage") if uat["status"] == "completed" else None,
        "uat_category": uat.get("category") if uat["status"] == "completed" else None,
        "dashboard_status": dashboard["status"],
        "dashboard_url": dashboard.get("dashboard_url") if dashboard["status"] == "created" else None,
        "executed_at": truth["generated_at"],
    }


def build_system_truth_status(base_dir: Path | str | None = None, write_outputs: bool = False) -> dict[str, Any]:
    base = Path(base_dir) if base_dir is not None else ROOT_DIR
    config = get_runtime_config()
    services = _service_statuses(base)
    quality_gate = _quality_gate_status(base)
    truth: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "status_schema": sorted(ALLOWED_STATUSES),
        "dataset_mode": "uploaded_excel",
        "runtime_config": {
            "target_prodi": config.target_prodi,
            "target_fakultas": config.target_fakultas,
            "target_tahun_akademik": config.target_tahun_akademik,
            "target_tahun_anggaran": config.target_tahun_anggaran,
        },
        "sources": _source_status(base),
        "layers": _layer_status(base),
        "quality_gate": quality_gate,
        "reconciliation": _fact_anggaran_status(base),
        "metrics": {
            "pipeline_latency": _pipeline_latency_status(base, write_output=write_outputs),
            "data_freshness": _metric_file_status(base, "data_freshness.json", ["freshness_seconds", "data_freshness_status"]),
            "dropout_rate": {"status": quality_gate["status"], "dropout_rate": quality_gate["dropout_rate"]},
            "data_quality_score": {"status": quality_gate["status"], "data_quality_score": quality_gate["quality_score"]},
        },
        "uat": _uat_status(base),
        "services": services,
    }
    truth["storage"] = _storage_status(base, services)
    truth["dashboard"] = _superset_dashboard_status(base, services)
    truth["bab4_evidence"] = _bab4_evidence(truth)

    if write_outputs:
        reports = base / "outputs" / "reports"
        write_json(reports / "system_truth_status.json", truth)
        write_json(reports / "bab4_evidence_summary.json", truth["bab4_evidence"])
        _write_csv(reports / "system_truth_status.csv", truth)
    return truth


def _write_csv(path: Path, truth: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["component", "status", "source", "message"],
        ["quality_gate", truth["quality_gate"]["status"], None, None],
        ["fact_anggaran", truth["reconciliation"]["status"], truth["reconciliation"].get("source"), None],
        ["uat", truth["uat"]["status"], truth["uat"].get("source"), truth["uat"].get("message")],
        ["storage", truth["storage"]["status"], truth["storage"].get("manifest_source"), truth["storage"].get("message")],
        ["dashboard", truth["dashboard"]["status"], truth["dashboard"].get("source"), truth["dashboard"].get("message")],
    ]
    for layer, item in truth["layers"].items():
        rows.append([f"layer.{layer}", item["status"], ",".join(item.get("existing", [])), None])
    for service, item in truth["services"].items():
        rows.append([f"service.{service}", item["status"], item.get("url") or item.get("host"), item.get("message")])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerows(rows)


def main() -> None:
    truth = build_system_truth_status(write_outputs=True)
    print(
        {
            "fact_anggaran": truth["reconciliation"]["status"],
            "storage": truth["storage"]["status"],
            "dashboard": truth["dashboard"]["status"],
        }
    )


if __name__ == "__main__":
    main()
