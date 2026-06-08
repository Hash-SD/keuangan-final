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

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import ROOT_DIR
from src.common.runtime_config import get_runtime_config
from src.common.time_utils import utc_now_iso


ALLOWED_STATUSES = {
    "not_started",
    "missing",
    "generated",
    "validated",
    "rejected",
    "ready",
    "configured",
    "mapped",
    "uploaded",
    "failed",
    "not_available",
    "manual_input_required",
    "fallback",
    "empty",
    "unreachable",
    "inconsistent",
    "skipped",
    "created",
    "configured_unreachable",
    "completed",
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
    elif any(path.is_dir() and _file_count(path) == 0 for path in paths if path.exists()):
        status = "empty"
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


def _configured_value(value: Any, source: str = "runtime_config") -> dict[str, Any]:
    return {
        "configured_value": value,
        "detected_value": None,
        "validated_value": None,
        "status": "not_started",
        "source": source,
        "message": "Nilai konfigurasi tersedia tetapi belum ada hasil proses.",
    }


def _source_status(base_dir: Path) -> dict[str, Any]:
    raw_dir = base_dir / "data" / "raw"
    layers = {
        "pdf": list((raw_dir / "pdf").glob("*.pdf")),
        "csv": list((raw_dir / "csv").glob("*.csv")),
        "excel": list((raw_dir / "excel").glob("*.xlsx")),
    }
    result = {}
    for source_type, files in layers.items():
        result[source_type] = {
            "status": "ready" if files else "missing",
            "file_count": len(files),
            "files": [_rel(path, base_dir) for path in sorted(files)],
            "message": "Artefak sumber tersedia." if files else "Artefak sumber belum tersedia.",
        }
    return result


def _layer_status(base_dir: Path) -> dict[str, Any]:
    generated = base_dir / "data" / "generated"
    return {
        "raw": _artifact_status([base_dir / "data" / "raw"], base_dir),
        "bronze": _artifact_status(
            [
                generated / "bronze" / "ingestion_metadata.json",
                generated / "bronze" / "csv_transactions_valid.csv",
            ],
            base_dir,
        ),
        "silver": _artifact_status(
            [
                generated / "silver" / "fact_piutang_ukt_prodi.csv",
                generated / "silver" / "transactions_clean.csv",
                generated / "silver" / "silver_rab.csv",
            ],
            base_dir,
        ),
        "gold": _artifact_status(
            [
                generated / "gold" / "fact_piutang_ukt_prodi.csv",
                generated / "gold" / "dim_organisasi.csv",
                generated / "gold" / "dim_mahasiswa.csv",
                generated / "gold" / "dim_kualitas_piutang.csv",
                generated / "gold" / "dim_waktu_tunggakan.csv",
                generated / "gold" / "vw_dashboard_piutang_ukt.csv",
            ],
            base_dir,
        ),
        "quarantine": _artifact_status([base_dir / "data" / "quarantine" / "logs"], base_dir),
        "metrics": _artifact_status([base_dir / "outputs" / "metrics"], base_dir),
        "reports": _artifact_status([base_dir / "outputs" / "reports"], base_dir),
    }


def _quality_gate_status(base_dir: Path) -> dict[str, Any]:
    summary_path = base_dir / "data" / "quarantine" / "logs" / "quality_gate_summary.json"
    rejected_path = base_dir / "data" / "quarantine" / "logs" / "rejected_rows.csv"
    payload = _read_json(summary_path)
    if not payload:
        return {
            "status": "missing",
            "total_rows": _value(None, "missing", None, "Quality Gate belum dijalankan."),
            "valid_rows": _value(None, "missing", None, "Quality Gate belum dijalankan."),
            "rejected_rows": _value(None, "missing", None, "Quality Gate belum dijalankan."),
            "dropout_rate": _value(None, "missing", None, "Quality Gate belum dijalankan."),
        }
    source = _rel(summary_path, base_dir)
    if payload.get("_error"):
        status = "failed"
        message = f"Quality Gate summary tidak valid: {payload['_error']}"
    else:
        rejected_count = _csv_row_count(rejected_path)
        expected_rejected = payload.get("rejected_rows")
        status = "validated"
        message = "Nilai dibaca dari hasil Quality Gate yang tersedia."
        if rejected_count is not None and expected_rejected is not None and rejected_count != expected_rejected:
            status = "inconsistent"
            message = "Jumlah rejected_rows tidak konsisten dengan rejected_rows.csv."
    return {
        "status": status,
        "total_rows": _value(payload.get("total_rows"), status, source, message),
        "valid_rows": _value(payload.get("valid_rows"), status, source, message),
        "rejected_rows": _value(payload.get("rejected_rows"), status, source, message),
        "dropout_rate": _value(payload.get("dropout_rate"), status, source, message),
        "rejected_rows_file": _rel(rejected_path, base_dir) if rejected_path.exists() else None,
    }


def _reconcile_status(base_dir: Path) -> dict[str, Any]:
    path = base_dir / "outputs" / "metrics" / "reconcile_control_total.json"
    payload = _read_json(path)
    if not payload:
        return {
            "status": "missing",
            "total_piutang": _value(None, "missing", None, "Rekonsiliasi belum dijalankan."),
            "jumlah_penunggak": _value(None, "missing", None, "Rekonsiliasi belum dijalankan."),
        }
    status = "validated" if str(payload.get("status", "")).lower() == "pass" else "failed"
    source = _rel(path, base_dir)
    message = "Rekonsiliasi tersedia dan status pass." if status == "validated" else "Rekonsiliasi tersedia tetapi tidak pass."
    return {
        "status": status,
        "raw_status": payload.get("status"),
        "total_piutang": _value(payload.get("total_piutang"), status, source, message),
        "jumlah_penunggak": _value(payload.get("jumlah_penunggak"), status, source, message),
        "target_total_piutang": _value(payload.get("target_total_piutang"), status, source, message),
        "target_jumlah_penunggak": _value(payload.get("target_jumlah_penunggak"), status, source, message),
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
        **{
            key: _value(payload.get(key), status, source, "Nilai dibaca dari artefak metrik.")
            for key in keys
        },
        "source": source,
    }


def _uat_status(base_dir: Path) -> dict[str, Any]:
    uat_dir = base_dir / "outputs" / "uat"
    template = uat_dir / "uat_template.csv"
    responses = uat_dir / "uat_dummy_response.csv"
    summary = uat_dir / "uat_score_summary.json"
    matrix = uat_dir / "uat_matrix_summary.json"
    template_available = template.exists()
    responses_available = responses.exists() and (_csv_row_count(responses) or 0) > 0
    summary_payload = _read_json(summary)
    matrix_payload = _read_json(matrix)

    if not template_available:
        status = "missing"
        message = "Instrumen UAT belum tersedia."
        source = None
    elif not responses_available:
        status = "manual_input_required"
        message = "Instrumen tersedia tetapi belum ada penilaian."
        source = _rel(template, base_dir)
    elif not summary_payload or not matrix_payload:
        status = "not_available"
        message = "Respons tersedia tetapi hasil UAT belum dihitung."
        source = _rel(responses, base_dir)
    else:
        status = "completed"
        message = "Hasil UAT dibaca dari artefak penilaian."
        source = _rel(matrix, base_dir)

    respondent_count = 0
    if summary_payload:
        respondent_count = int(summary_payload.get("respondent_count") or 0)
    elif responses_available:
        respondent_count = _csv_row_count(responses) or 0

    return {
        "uat_status": status,
        "status": status,
        "template_available": template_available,
        "responses_available": responses_available,
        "respondent_count": respondent_count if status == "completed" else 0,
        "average_score": summary_payload.get("average_score") if status == "completed" and summary_payload else None,
        "percentage": summary_payload.get("percentage") if status == "completed" and summary_payload else None,
        "category": summary_payload.get("category") if status == "completed" and summary_payload else None,
        "source": source,
        "message": message,
        "matrix": matrix_payload if status == "completed" else None,
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
        completed = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=base_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception as exc:
        return {"status": "unreachable", "message": f"Docker engine tidak dapat diakses: {exc}", "services": []}
    if completed.returncode != 0:
        return {
            "status": "unreachable",
            "message": "Superset live validation belum dapat dijalankan karena Docker engine tidak aktif.",
            "stderr": completed.stderr.strip(),
            "services": [],
        }
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
    mapping_path = base_dir / "outputs" / "reports" / "storage_mapping.json"
    manifest_path = base_dir / "outputs" / "reports" / "storage_manifest.json"
    mapping = _read_json(mapping_path)
    manifest = _read_json(manifest_path)
    minio_service = services.get("minioApi", {})
    upload = (manifest or {}).get("upload", {})
    if not mapping and not manifest:
        status = "not_started"
        message = "Storage manifest belum dibuat."
    elif minio_service.get("status") == "unreachable":
        status = "configured_unreachable"
        message = "Mapping storage tersedia, tetapi endpoint MinIO tidak dapat dijangkau."
    elif upload.get("status") == "uploaded":
        status = "uploaded"
        message = "Upload MinIO dilaporkan berhasil oleh manifest."
    elif upload.get("status") == "skipped":
        status = "skipped"
        message = "Upload MinIO tidak dijalankan; layer hanya mapped."
    else:
        status = "mapped"
        message = "Mapping storage tersedia."
    return {
        "status": status,
        "mapping_source": _rel(mapping_path, base_dir) if mapping_path.exists() else None,
        "manifest_source": _rel(manifest_path, base_dir) if manifest_path.exists() else None,
        "mapping": mapping,
        "manifest": manifest,
        "message": message,
    }


def _superset_dashboard_status(base_dir: Path, services: dict[str, Any]) -> dict[str, Any]:
    assets_path = base_dir / "outputs" / "reports" / "superset_assets.json"
    dashboard_path = base_dir / "outputs" / "reports" / "superset_dashboard.json"
    dashboard = _read_json(dashboard_path)
    assets = _read_json(assets_path)
    service_status = services.get("superset", {}).get("status")
    if service_status == "unreachable":
        return {
            "status": "unreachable",
            "source": _rel(dashboard_path, base_dir) if dashboard_path.exists() else None,
            "message": "Superset live validation belum dapat dijalankan karena layanan tidak aktif.",
            "dashboard_url": (dashboard or {}).get("dashboard_url"),
        }
    if dashboard and assets:
        return {
            "status": "created",
            "source": _rel(dashboard_path, base_dir),
            "message": "Artefak dashboard tersedia dan layanan Superset dapat dijangkau.",
            "dashboard_url": dashboard.get("dashboard_url"),
        }
    return {"status": "configured" if assets else "not_started", "source": None, "message": "Dashboard Superset belum divalidasi."}


def _bab4_evidence(truth: dict[str, Any]) -> dict[str, Any]:
    def available_metric(section: dict[str, Any], key: str) -> Any:
        item = section.get(key, {})
        return item.get("value") if item.get("status") in {"validated", "completed"} else None

    reconcile = truth["reconciliation"]
    quality_gate = truth["quality_gate"]
    quality = truth["metrics"]["data_quality_score"]
    uat = truth["uat"]
    storage = truth["storage"]
    dashboard = truth["dashboard"]
    return {
        "status": "ready" if reconcile["status"] == "validated" else "not_available",
        "message": "Ringkasan Bab 4 hanya memuat hasil yang tersedia." if reconcile["status"] == "validated" else "Hasil belum tersedia.",
        "total_piutang_target_prodi": available_metric(reconcile, "total_piutang"),
        "jumlah_penunggak_target_prodi": available_metric(reconcile, "jumlah_penunggak"),
        "total_rows_transaksi": available_metric(quality_gate, "total_rows"),
        "valid_rows": available_metric(quality_gate, "valid_rows"),
        "rejected_rows": available_metric(quality_gate, "rejected_rows"),
        "dropout_rate": available_metric(quality_gate, "dropout_rate"),
        "data_quality_score": quality.get("data_quality_score", {}).get("value"),
        "storage_status": storage["status"],
        "uat_average": uat["average_score"] if uat["status"] == "completed" else None,
        "uat_percentage": uat["percentage"] if uat["status"] == "completed" else None,
        "uat_category": uat["category"] if uat["status"] == "completed" else None,
        "dashboard_status": dashboard["status"],
        "dashboard_url": dashboard.get("dashboard_url") if dashboard["status"] == "created" else None,
        "executed_at": truth["generated_at"],
    }


def build_system_truth_status(base_dir: Path | str | None = None, write_outputs: bool = False) -> dict[str, Any]:
    base = Path(base_dir) if base_dir is not None else ROOT_DIR
    config = get_runtime_config()
    services = _service_statuses(base)
    truth: dict[str, Any] = {
        "generated_at": utc_now_iso(),
        "status_schema": sorted(ALLOWED_STATUSES),
        "runtime_config": {
            "target_prodi": config.target_prodi,
            "target_tahun_akademik": config.target_tahun_akademik,
            "target_total_piutang": _configured_value(config.target_total_piutang),
            "target_jumlah_penunggak": _configured_value(config.target_jumlah_penunggak),
        },
        "sources": _source_status(base),
        "layers": _layer_status(base),
        "quality_gate": _quality_gate_status(base),
        "reconciliation": _reconcile_status(base),
        "metrics": {
            "pipeline_latency": _metric_file_status(base, "pipeline_latency.json", ["latency_seconds", "pipeline_latency_seconds"]),
            "data_freshness": _metric_file_status(base, "data_freshness.json", ["freshness_seconds", "data_freshness_status"]),
            "dropout_rate": _metric_file_status(base, "dropout_rate.json", ["dropout_rate", "total_rows", "valid_rows", "rejected_rows"]),
            "data_quality_score": _metric_file_status(base, "data_quality_score.json", ["data_quality_score", "completeness", "validity", "consistency", "accuracy"]),
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
        ["reconciliation", truth["reconciliation"]["status"], truth["reconciliation"].get("source"), None],
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
            "quality_gate": truth["quality_gate"]["status"],
            "reconciliation": truth["reconciliation"]["status"],
            "uat": truth["uat"]["status"],
            "storage": truth["storage"]["status"],
            "dashboard": truth["dashboard"]["status"],
        }
    )


if __name__ == "__main__":
    main()
