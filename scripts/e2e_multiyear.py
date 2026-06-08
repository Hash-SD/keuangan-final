from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from portal_backend.app import create_app
from portal_backend.services.upload_session import reset_session
from src.common.logging_utils import write_json
from src.common.time_utils import utc_now_iso


REPORTS = ROOT / "outputs" / "reports"
LOGS = ROOT / "outputs" / "logs" / "e2e"
SCREENSHOTS = ROOT / "outputs" / "screenshots"
SNAPSHOTS = ROOT / "outputs" / "evidence" / "multiyear"
GENERATED_DUMMY = ROOT / "data" / "generated" / "dummy"


@dataclass(frozen=True)
class DatasetSpec:
    dataset_session_id: str
    tahun_akademik: str
    tahun_anggaran: str
    seed: int
    target_total_piutang: int
    target_jumlah_penunggak: int


DATASETS = [
    DatasetSpec("dummy-2024", "2023/2024", "2024", 2024001, 31_250_000, 15),
    DatasetSpec("dummy-2025", "2024/2025", "2025", 2025001, 35_000_000, 16),
    DatasetSpec("dummy-2026", "2025/2026", "2026", 2026001, 39_500_000, 17),
]


SKILL_SUMMARY = {
    "local_find_skills_command": "not_found",
    "fallback_command": "npx skills find <keyword>",
    "keywords": [
        "python",
        "pandas",
        "multi-year dataset",
        "data generation",
        "airflow",
        "docker",
        "minio",
        "s3",
        "superset",
        "flask",
        "portal",
        "playwright",
        "pytest",
        "production readiness",
        "observability",
        "logging",
        "end-to-end test",
    ],
    "relevant_local_skills_used": [
        "find-skills",
        "airflow-dag-patterns",
        "browser:control-in-app-browser",
    ],
    "notable_global_results": {
        "pandas": ["shubhamsaboo/awesome-llm-apps@data-analyst"],
        "airflow": ["astronomer/agents@airflow"],
        "playwright": ["openai/skills@playwright"],
        "pytest": ["github/awesome-copilot@pytest-coverage"],
        "superset": ["membranedev/application-skills@apache-superset"],
        "s3": ["aj-geddes/useful-ai-prompts@aws-s3-management", "itsmostafa/aws-agent-skills@s3"],
    },
}

CONTEXT7_SUMMARY = [
    {"library": "pandas", "library_id": "/websites/pandas_pydata", "used_for": "read_csv, read_excel, missing-column validation, groupby/aggregation by period"},
    {"library": "openpyxl", "library_id": "/websites/openpyxl_readthedocs_io_en_stable", "used_for": "read-only workbook load, sheetnames, header validation"},
    {"library": "pypdf", "library_id": "/websites/pypdf_readthedocs_io_en_stable", "used_for": "PdfReader validation and text extraction"},
    {"library": "Flask", "library_id": "/pallets/flask", "used_for": "request.files upload flow and JSON response validation"},
    {"library": "Playwright", "library_id": "/microsoft/playwright", "used_for": "file upload, locators, screenshots, console errors"},
    {"library": "Airflow", "library_id": "/apache/airflow", "used_for": "task dependency and parameterized DAG review"},
    {"library": "MinIO", "library_id": "/minio/minio-py", "used_for": "S3-compatible bucket/object mapping expectations"},
    {"library": "Superset", "library_id": "/apache/superset", "used_for": "dataset, chart, dashboard, native-filter API expectations"},
]


def ensure_dirs() -> None:
    for path in [REPORTS, LOGS, SCREENSHOTS, SNAPSHOTS, GENERATED_DUMMY]:
        path.mkdir(parents=True, exist_ok=True)


def append_log(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"timestamp": utc_now_iso(), **entry}, ensure_ascii=False) + "\n")


def run_command(step_name: str, args: list[str], spec: DatasetSpec | None = None, extra_env: dict[str, str] | None = None, log_name: str = "e2e_master.log") -> dict[str, Any]:
    env = os.environ.copy()
    if spec:
        env.update(env_for(spec))
    if extra_env:
        env.update(extra_env)
    started = time.perf_counter()
    completed = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    duration = round(time.perf_counter() - started, 3)
    result = {
        "step_name": step_name,
        "dataset_session_id": spec.dataset_session_id if spec else None,
        "tahun_akademik": spec.tahun_akademik if spec else None,
        "tahun_anggaran": spec.tahun_anggaran if spec else None,
        "command": " ".join(args),
        "status": "success" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "duration_seconds": duration,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
        "error_message": completed.stderr[-1000:] if completed.returncode else None,
    }
    append_log(LOGS / log_name, result)
    append_log(LOGS / "e2e_master.log", result)
    return result


def env_for(spec: DatasetSpec) -> dict[str, str]:
    return {
        "DATASET_MODE": "uploaded",
        "PORTAL_TARGET_PRODI": "Sains Data",
        "PORTAL_TARGET_FAKULTAS": "Fakultas Sains",
        "PORTAL_TARGET_TAHUN_AKADEMIK": spec.tahun_akademik,
        "PORTAL_TARGET_TAHUN_ANGGARAN": spec.tahun_anggaran,
        "PORTAL_BATCH_ID": spec.dataset_session_id,
        "PORTAL_DUMMY_SEED": str(spec.seed),
        "PORTAL_TARGET_TOTAL_PIUTANG": str(spec.target_total_piutang),
        "PORTAL_TARGET_JUMLAH_PENUNGGAK": str(spec.target_jumlah_penunggak),
    }


@contextmanager
def patched_env(values: dict[str, str]):
    old = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"value": payload}
    except json.JSONDecodeError as exc:
        return {"_error": str(exc)}


def copy_if_exists(source: Path, target: Path) -> str | None:
    if not source.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        shutil.copy2(source, target)
    return str(target)


def generate_dataset(spec: DatasetSpec) -> dict[str, Any]:
    args = [
        sys.executable,
        "src/generators/generate_all.py",
        "--tahun-akademik",
        spec.tahun_akademik,
        "--tahun-anggaran",
        spec.tahun_anggaran,
        "--dataset-session-id",
        spec.dataset_session_id,
        "--seed",
        str(spec.seed),
        "--target-total-piutang",
        str(spec.target_total_piutang),
        "--target-jumlah-penunggak",
        str(spec.target_jumlah_penunggak),
        "--output-root",
        str(GENERATED_DUMMY),
    ]
    command = run_command("generate_dummy", args, spec, log_name="e2e_generate_dummy.log")
    summary = read_json(REPORTS / f"data_generation_{spec.dataset_session_id}.json")
    append_log(LOGS / f"{spec.dataset_session_id}-upload.log", {"step_name": "generated_files_ready", "dataset_session_id": spec.dataset_session_id, "status": command["status"], "output": summary})
    return {**summary, "command_status": command["status"]}


def upload_and_commit(spec: DatasetSpec) -> dict[str, Any]:
    app = create_app()
    with patched_env(env_for(spec)):
        with app.test_client() as client:
            reset_session()
            context = {
                "target_prodi": "Sains Data",
                "target_fakultas": "Fakultas Sains",
                "target_tahun_akademik": spec.tahun_akademik,
                "target_tahun_anggaran": spec.tahun_anggaran,
                "target_label": f"Sains Data - Tahun Akademik {spec.tahun_akademik}",
                "batch_id": spec.dataset_session_id,
            }
            client.post("/api/upload/session/context", json=context)
            base = GENERATED_DUMMY / spec.dataset_session_id
            files = [
                ("pdf", base / "pdf" / f"laporan_audited_{spec.tahun_anggaran}.pdf", "application/pdf"),
                ("csv", base / "csv" / "transaksi_ganjil.csv", "text/csv"),
                ("csv", base / "csv" / "transaksi_genap.csv", "text/csv"),
                ("excel", base / "excel" / f"rab_{spec.tahun_anggaran}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
            ]
            for upload_type, path, content_type in files:
                with path.open("rb") as handle:
                    data = {"upload_type": upload_type, "file": (io.BytesIO(handle.read()), path.name, content_type)}
                response = client.post("/api/upload/session/file", data=data, content_type="multipart/form-data")
                if response.status_code >= 400:
                    raise RuntimeError(f"Upload {path} failed: {response.status_code} {response.get_data(as_text=True)}")
            status_before_commit = client.get("/api/upload/session/status").get_json()
            commit_response = client.post("/api/upload/session/commit")
            commit_payload = commit_response.get_json()
    result = {
        "dataset_session_id": spec.dataset_session_id,
        "tahun_akademik": spec.tahun_akademik,
        "tahun_anggaran": spec.tahun_anggaran,
        "status_before_commit": status_before_commit,
        "commit_status_code": commit_response.status_code,
        "commit": commit_payload,
        "status": "success" if commit_response.status_code == 200 and commit_payload.get("status") == "committed" else "failed",
    }
    append_log(LOGS / "e2e_upload_session.log", {"step_name": "upload_commit", **result})
    append_log(LOGS / f"{spec.dataset_session_id}-upload.log", {"step_name": "upload_commit", **result})
    return result


def pipeline_commands() -> list[tuple[str, list[str], str]]:
    return [
        ("quality_gate", [sys.executable, "src/validation/quality_gate.py"], "e2e_quality_gate.log"),
        ("bronze", [sys.executable, "src/transformations/bronze_ingest.py"], "e2e_bronze.log"),
        ("silver", [sys.executable, "src/transformations/silver_clean.py"], "e2e_silver.log"),
        ("gold", [sys.executable, "src/transformations/gold_star_schema.py"], "e2e_gold.log"),
        ("reconcile", [sys.executable, "src/metrics/reconcile_control_total.py"], "e2e_metrics.log"),
        ("dropout_rate", [sys.executable, "src/metrics/dropout_rate.py"], "e2e_metrics.log"),
        ("data_quality_score", [sys.executable, "src/metrics/data_quality_score.py"], "e2e_metrics.log"),
        ("pipeline_latency", [sys.executable, "src/metrics/pipeline_latency.py"], "e2e_metrics.log"),
        ("data_freshness", [sys.executable, "src/metrics/data_freshness.py"], "e2e_metrics.log"),
        ("storage_manifest", [sys.executable, "src/storage/storage_manifest.py"], "e2e_minio.log"),
        ("system_truth", [sys.executable, "src/status/system_truth_status.py"], "e2e_pipeline.log"),
    ]


def run_pipeline(spec: DatasetSpec) -> dict[str, Any]:
    steps = []
    for step_name, args, log_name in pipeline_commands():
        result = run_command(step_name, args, spec, log_name=log_name)
        steps.append(result)
        append_log(LOGS / f"{spec.dataset_session_id}-pipeline.log", result)
        if result["status"] != "success":
            break
    layer_snapshot_dir = SNAPSHOTS / spec.dataset_session_id
    snapshot_paths = {
        "bronze": copy_if_exists(ROOT / "data" / "generated" / "bronze", layer_snapshot_dir / "bronze"),
        "silver": copy_if_exists(ROOT / "data" / "generated" / "silver", layer_snapshot_dir / "silver"),
        "gold": copy_if_exists(ROOT / "data" / "generated" / "gold", layer_snapshot_dir / "gold"),
        "quarantine": copy_if_exists(ROOT / "data" / "quarantine" / "logs", layer_snapshot_dir / "quarantine" / "logs"),
        "metrics": copy_if_exists(ROOT / "outputs" / "metrics", layer_snapshot_dir / "metrics"),
        "reports": copy_if_exists(ROOT / "outputs" / "reports", layer_snapshot_dir / "reports"),
    }
    result = {
        "dataset_session_id": spec.dataset_session_id,
        "tahun_akademik": spec.tahun_akademik,
        "tahun_anggaran": spec.tahun_anggaran,
        "status": "success" if all(step["status"] == "success" for step in steps) else "failed",
        "steps": steps,
        "snapshots": snapshot_paths,
    }
    return result


def row_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8", newline="") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def validate_layers(spec: DatasetSpec) -> dict[str, Any]:
    snapshot = SNAPSHOTS / spec.dataset_session_id
    checks = {
        "staging": [
            ROOT / "data" / "uploads" / "staging",
        ],
        "raw": [
            ROOT / "data" / "raw" / "pdf" / spec.tahun_anggaran.replace("/", "-"),
            ROOT / "data" / "raw" / "csv" / spec.tahun_akademik.replace("/", "-"),
            ROOT / "data" / "raw" / "excel" / spec.tahun_anggaran.replace("/", "-"),
        ],
        "bronze": [snapshot / "bronze" / "ingestion_metadata.json", snapshot / "bronze" / "csv_transactions_valid.csv"],
        "silver": [
            snapshot / "silver" / "transactions_clean.csv",
            snapshot / "silver" / "fact_piutang_ukt_prodi.csv",
            snapshot / "silver" / "dim_kualitas_piutang.csv",
            snapshot / "silver" / "silver_rab.csv",
        ],
        "gold": [
            snapshot / "gold" / "fact_piutang_ukt_prodi.csv",
            snapshot / "gold" / "dim_organisasi.csv",
            snapshot / "gold" / "dim_mahasiswa.csv",
            snapshot / "gold" / "dim_kualitas_piutang.csv",
            snapshot / "gold" / "dim_waktu_tunggakan.csv",
            snapshot / "gold" / "vw_dashboard_piutang_ukt.csv",
        ],
        "quarantine": [snapshot / "quarantine" / "logs" / "quality_gate_summary.json", snapshot / "quarantine" / "logs" / "rejected_rows.csv"],
        "metrics": [
            snapshot / "metrics" / "pipeline_latency.json",
            snapshot / "metrics" / "data_freshness.json",
            snapshot / "metrics" / "dropout_rate.json",
            snapshot / "metrics" / "data_quality_score.json",
            snapshot / "metrics" / "reconcile_control_total.json",
        ],
        "reports": [
            snapshot / "reports" / "storage_manifest.json",
            snapshot / "reports" / "system_truth_status.json",
            snapshot / "reports" / "bab4_evidence_summary.json",
        ],
    }
    result = {}
    for layer, paths in checks.items():
        existing = [str(path) for path in paths if path.exists()]
        result[layer] = {
            "status": "ready" if len(existing) == len(paths) else "missing",
            "required": [str(path) for path in paths],
            "existing": existing,
        }
    metadata = read_json(snapshot / "bronze" / "ingestion_metadata.json")
    quality = read_json(snapshot / "quarantine" / "logs" / "quality_gate_summary.json")
    reconcile = read_json(snapshot / "metrics" / "reconcile_control_total.json")
    result["dataset_session_id"] = spec.dataset_session_id
    result["tahun_akademik"] = spec.tahun_akademik
    result["tahun_anggaran"] = spec.tahun_anggaran
    result["bronze_dataset_session_id"] = metadata.get("upload_session_id")
    result["quality_gate"] = quality
    result["reconcile"] = reconcile
    return result


def minio_mapping_by_year(spec: DatasetSpec) -> dict[str, Any]:
    manifest = read_json(SNAPSHOTS / spec.dataset_session_id / "reports" / "storage_manifest.json")
    layers = {}
    for name, payload in (manifest.get("layers") or {}).items():
        layers[name] = {
            "local_path": payload.get("local_path"),
            "s3_prefix": payload.get("s3_prefix"),
            "file_count": payload.get("file_count"),
            "total_size_bytes": payload.get("total_size_bytes"),
            "status": payload.get("status"),
            "storage_status": payload.get("storage_status"),
            "upload_status": (manifest.get("upload") or {}).get("status"),
        }
    return {
        "dataset_session_id": spec.dataset_session_id,
        "tahun_akademik": spec.tahun_akademik,
        "tahun_anggaran": spec.tahun_anggaran,
        "minio_endpoint": manifest.get("minio_endpoint"),
        "bucket": manifest.get("bucket"),
        "upload": manifest.get("upload"),
        "layers": layers,
    }


def chart_values(spec: DatasetSpec) -> dict[str, Any]:
    dashboard_path = SNAPSHOTS / spec.dataset_session_id / "gold" / "vw_dashboard_piutang_ukt.csv"
    if not dashboard_path.exists():
        return {"status": "missing", "charts": {}}
    df = pd.read_csv(dashboard_path)
    target = df[(df["tahun_akademik"].astype(str) == spec.tahun_akademik) & (df["tahun_anggaran"].astype(str) == spec.tahun_anggaran)]
    charts = {
        "total_piutang": {"value": int(target["nominal_piutang_rp"].sum()) if not target.empty else 0, "status": "validated" if not target.empty else "missing"},
        "jumlah_penunggak": {"value": int(target["nim"].nunique()) if "nim" in target else int(len(target)), "status": "validated" if not target.empty else "missing"},
        "piutang_per_prodi": {"status": "validated" if not target.empty else "missing"},
        "distribusi_kualitas": {"status": "validated" if not target.empty else "missing"},
        "tren_semester": {"status": "validated" if not target.empty else "missing"},
        "detail_mahasiswa": {"status": "validated" if not target.empty else "missing"},
    }
    return {"status": "validated" if not target.empty else "missing", "charts": charts}


def write_csv_report(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flat_rows = []
    for row in rows:
        flat_rows.append({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    if not flat_rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(flat_rows)


def validate_superset() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = run_command("setup_superset_dashboard", [sys.executable, "src/sql/setup_superset_dashboard.py"], log_name="e2e_superset.log")
    status = {
        "status": "validated" if result["status"] == "success" else "unreachable",
        "command": result["command"],
        "error_message": result["error_message"],
        "warning": None if result["status"] == "success" else "Superset offline or prerequisite assets unavailable; live dashboard validation not claimed.",
        "source_log": str(LOGS / "e2e_superset.log"),
    }
    filters = {
        "status": status["status"],
        "required_filters": ["Tahun Akademik", "Tahun Anggaran", "Semester", "Prodi", "Kualitas Piutang"],
        "validated_live": result["status"] == "success",
    }
    dashboard = read_json(REPORTS / "superset_dashboard.json")
    if dashboard:
        filters["native_filter_columns"] = dashboard.get("native_filter_columns")
    write_json(REPORTS / "superset_dashboard_status.json", status)
    write_json(REPORTS / "superset_filters_validation.json", filters)
    return status, {}, filters


def external_dependency_status() -> dict[str, Any]:
    docker_config = run_command("docker_compose_config", ["docker", "compose", "config"], log_name="e2e_master.log")
    ps = run_command("docker_compose_ps", ["docker", "compose", "ps"], log_name="e2e_master.log") if docker_config["status"] == "success" else {"status": "skipped", "warning": "docker compose config failed"}
    return {"docker_compose_config": docker_config, "docker_compose_ps": ps}


def build_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# E2E Multiyear Test Report",
        "",
        f"Generated at: {report['generated_at']}",
        f"Final decision: {report['final_decision']}",
        "",
        "## Dataset",
    ]
    for item in report["datasets"]:
        lines.append(f"- {item['dataset_session_id']} | {item['tahun_akademik']} | {item['tahun_anggaran']} | generator={item.get('status_generator')} | pipeline={item.get('pipeline_status')}")
    lines.extend(["", "## Validation Results"])
    for item in report["layer_validation"]:
        layer_status = {key: value["status"] for key, value in item.items() if isinstance(value, dict) and "status" in value}
        lines.append(f"- {item['dataset_session_id']}: {json.dumps(layer_status, ensure_ascii=False)}")
    lines.extend(["", "## Superset", json.dumps(report["superset_dashboard_status"], indent=2, ensure_ascii=False)])
    lines.extend(["", "## Errors And Warnings"])
    for error in report["errors_found"]:
        lines.append(f"- ERROR: {error}")
    for warning in report["dependency_warnings"]:
        lines.append(f"- WARNING: {warning}")
    lines.extend(["", "## Evidence Files"])
    for path in report["output_reports"]:
        lines.append(f"- {path}")
    for path in report["logs_created"]:
        lines.append(f"- {path}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ensure_dirs()
    write_json(REPORTS / "skill_discovery_summary.json", SKILL_SUMMARY)
    write_json(REPORTS / "context7_docs_used.json", {"documents": CONTEXT7_SUMMARY})

    generation = []
    uploads = []
    pipelines = []
    layer_validation = []
    minio = []
    charts = []
    errors: list[str] = []
    warnings: list[str] = []

    for spec in DATASETS:
        try:
            generation.append(generate_dataset(spec))
            uploads.append(upload_and_commit(spec))
            pipeline = run_pipeline(spec)
            pipelines.append(pipeline)
            if pipeline["status"] != "success":
                errors.append(f"{spec.dataset_session_id} pipeline failed")
            layer_validation.append(validate_layers(spec))
            minio.append(minio_mapping_by_year(spec))
            charts.append({"tahun_akademik": spec.tahun_akademik, "tahun_anggaran": spec.tahun_anggaran, **chart_values(spec)})
        except Exception as exc:
            errors.append(f"{spec.dataset_session_id}: {exc}")
            append_log(LOGS / "e2e_master.log", {"step_name": "dataset_exception", "dataset_session_id": spec.dataset_session_id, "status": "failed", "error_message": str(exc)})

    write_json(REPORTS / "data_generation_multiyear_summary.json", {"datasets": generation})
    write_csv_report(REPORTS / "data_generation_multiyear_summary.csv", generation)
    write_json(REPORTS / "e2e_upload_sessions.json", {"sessions": uploads})
    for source in ["dataset_registry.json", "available_periods.json"]:
        payload = read_json(REPORTS / source)
        write_json(REPORTS / source, payload)
    write_json(REPORTS / "e2e_pipeline_by_year.json", {"years": pipelines})
    write_csv_report(REPORTS / "e2e_pipeline_by_year.csv", [{"dataset_session_id": p["dataset_session_id"], "tahun_akademik": p["tahun_akademik"], "tahun_anggaran": p["tahun_anggaran"], "status": p["status"]} for p in pipelines])
    write_json(REPORTS / "minio_layer_mapping_by_year.json", {"years": minio})
    write_csv_report(REPORTS / "minio_layer_mapping_by_year.csv", minio)
    write_json(REPORTS / "superset_charts_by_year.json", {"years": charts})
    superset_status, _, superset_filters = validate_superset()
    if superset_status["status"] != "validated":
        warnings.append("Superset offline. Playwright Superset dashboard test skipped with external dependency warning.")
    deps = external_dependency_status()
    if deps["docker_compose_config"]["status"] != "success":
        warnings.append("Docker compose config failed or Docker unavailable; live MinIO/Superset/Airflow validation not claimed.")

    output_reports = [
        str(REPORTS / name)
        for name in [
            "data_generation_multiyear_summary.json",
            "data_generation_multiyear_summary.csv",
            "e2e_upload_sessions.json",
            "dataset_registry.json",
            "available_periods.json",
            "e2e_pipeline_by_year.json",
            "e2e_pipeline_by_year.csv",
            "minio_layer_mapping_by_year.json",
            "minio_layer_mapping_by_year.csv",
            "superset_dashboard_status.json",
            "superset_charts_by_year.json",
            "superset_filters_validation.json",
        ]
    ]
    logs_created = [str(path) for path in sorted(LOGS.glob("*.log"))]
    pipeline_ok = bool(pipelines) and all(item["status"] == "success" for item in pipelines) and len(pipelines) == len(DATASETS)
    upload_ok = bool(uploads) and all(item["status"] == "success" for item in uploads) and len(uploads) == len(DATASETS)
    layers_ok = all(all(value.get("status") == "ready" for key, value in item.items() if isinstance(value, dict) and key in {"raw", "bronze", "silver", "gold", "quarantine", "metrics", "reports"}) for item in layer_validation)
    local_ok = pipeline_ok and upload_ok and layers_ok and not errors
    final_decision = "ready_with_external_dependency_warning" if local_ok and warnings else "production_ready_candidate" if local_ok else "not_ready"
    report = {
        "generated_at": utc_now_iso(),
        "environment": {
            "python": sys.version,
            "cwd": str(ROOT),
            "dataset_mode": os.getenv("DATASET_MODE"),
            "minio_upload_enabled": os.getenv("MINIO_UPLOAD_ENABLED", "false"),
        },
        "skills_found": SKILL_SUMMARY,
        "context7_docs_used": CONTEXT7_SUMMARY,
        "mcp_used": ["Context7", "Browser/Playwright skill; CLI Playwright validation executed separately"],
        "datasets": [
            {
                **item,
                "pipeline_status": next((p["status"] for p in pipelines if p["dataset_session_id"] == item.get("dataset_session_id")), "missing"),
            }
            for item in generation
        ],
        "upload_sessions": uploads,
        "pipeline_by_year": pipelines,
        "layer_validation": layer_validation,
        "minio_layer_mapping": minio,
        "superset_dashboard_status": superset_status,
        "superset_filters_validation": superset_filters,
        "superset_charts_by_year": charts,
        "screenshots": [str(path) for path in sorted(SCREENSHOTS.glob("*.png"))],
        "logs_created": logs_created,
        "output_reports": output_reports,
        "external_dependencies": deps,
        "errors_found": errors,
        "dependency_warnings": warnings,
        "final_decision": final_decision,
    }
    write_json(REPORTS / "e2e_multiyear_test_report.json", report)
    (REPORTS / "e2e_multiyear_test_report.md").write_text(build_markdown(report), encoding="utf-8")
    print(json.dumps({"final_decision": final_decision, "errors": errors, "warnings": warnings, "report": str(REPORTS / "e2e_multiyear_test_report.json")}, indent=2))
    return 0 if final_decision != "not_ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
