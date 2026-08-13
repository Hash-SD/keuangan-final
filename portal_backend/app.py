from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from threading import Lock

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from src.common.runtime_paths import raw_rab_path
from src.status.system_truth_status import build_system_truth_status
from src.validation.dataset_contract import validate_committed_dataset

from .services import excel_upload
from .services.activity import append_activity, read_activities
from .services.airflow import (
    create_pipeline_run_id,
    get_active_dag_run,
    get_all_dag_runs,
    get_dag_run,
    get_latest_dag_run,
    get_runtime_snapshot,
    purge_stale_queued_runs,
    trigger_dag,
)
from .services.excel_lakehouse import excel_lakehouse_status
from .services.excel_upload import commit_excel_lakehouse_dataset
from .services.files import csv_preview, read_json, relative_path, resolve_preview_file
from .services.iku_review import (
    iku_review_queue,
    mapping_review_queue,
    save_iku_override,
)
from .services.lakehouse import lakehouse_summary
from .services.local_dashboard import (
    dashboard_section,
    read_superset_reference,
    write_dashboard_reports,
)
from .services.metrics import metrics_payload
from .services.paths import OUTPUTS_DIR, PORTAL_DIR
from .services.pipeline import run_command_group, run_full
from .services.production_state import production_readiness
from .services.superset_api import (
    fetch_superset_fact_rows,
    list_superset_dashboards,
    list_superset_databases,
)
from .services.system_status import service_statuses

_airflow_trigger_lock = Lock()


def _no_store_json(payload):
    response = jsonify(payload)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return response


def _safe_relative_path(path):
    try:
        return relative_path(path)
    except ValueError:
        return str(path)


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(PORTAL_DIR), static_url_path="")
    max_upload_mb = int(os.getenv("PORTAL_MAX_UPLOAD_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    @app.before_request
    def require_portal_token_for_mutations():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"} or not request.path.startswith("/api/"):
            return None
        if os.getenv("PORTAL_AUTH_REQUIRED", "false").strip().lower() not in {"1", "true", "yes", "on"}:
            return None
        expected = os.getenv("PORTAL_API_TOKEN", "").strip()
        if not expected:
            return jsonify({"status": "failed", "message": "PORTAL_API_TOKEN is not configured."}), 503
        provided = request.headers.get("X-Portal-Token", "").strip()
        if not provided:
            auth = request.headers.get("Authorization", "")
            provided = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else ""
        if provided != expected:
            return jsonify({"status": "failed", "message": "Authentication required."}), 401
        return None

    @app.after_request
    def add_cors_headers(response):
        origin = request.headers.get("Origin")
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, Authorization, X-Requested-With"
            )
            response.headers["Access-Control-Allow-Methods"] = (
                "GET, POST, PUT, DELETE, OPTIONS"
            )
        return response

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(
            {
                "status": "failed",
                "message": f"Ukuran file melebihi batas {max_upload_mb} MB.",
            }
        ), 413

    @app.get("/")
    @app.get("/v2")
    @app.get("/v2/")
    @app.get("/v2/index.html")
    @app.get("/legacy")
    @app.get("/legacy/")
    @app.get("/legacy/index.html")
    def index():
        return send_from_directory(PORTAL_DIR / "v2", "index.html")

    @app.get("/api/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "portal-backend",
                "mode": "local-on-premise",
                "basis": "excel_lakehouse_fact_anggaran",
            }
        )

    @app.get("/api/readiness")
    def readiness():
        checks = {}
        for name, path in {
            "outputs_reports": OUTPUTS_DIR / "reports",
            "raw_excel_lakehouse": PORTAL_DIR.parent
            / "data"
            / "raw"
            / "excel_lakehouse",
        }.items():
            checks[name] = {
                "status": "ready" if path.exists() else "missing",
                "path": relative_path(path),
            }
        truth = build_system_truth_status(write_outputs=False)
        manifest = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        checks["system_truth"] = {
            "status": "ready",
            "generated_at": truth.get("generated_at"),
        }
        checks["storage_manifest"] = {
            "status": "ready" if manifest and not manifest.get("_error") else "missing",
            "source": "outputs/reports/storage_manifest.json",
        }
        checks["superset"] = truth.get("services", {}).get(
            "superset", {"status": "unreachable"}
        )
        ready = all(
            item.get("status") in {"ready", "empty", "skipped", "mapped", "configured"}
            for item in checks.values()
        )
        return jsonify({"status": "ready" if ready else "not_ready", "checks": checks})

    @app.get("/api/production/readiness")
    def production_readiness_endpoint():
        payload = production_readiness()
        return jsonify(payload), 200 if payload[
            "status"
        ] == "READY_FOR_USER_UPLOAD" else 503

    @app.get("/api/superset/status")
    def superset_status():
        truth = build_system_truth_status(write_outputs=False)
        return jsonify(
            {
                "service": truth.get("services", {}).get(
                    "superset", {"status": "unreachable"}
                ),
                "dashboard": truth.get("dashboard", {"status": "not_started"}),
            }
        )

    @app.get("/api/superset/summary")
    def superset_summary():
        """Authoritative summary of fact_anggaran Gold layer metrics.

        The dashboard metric is the weighted annual allocation total.  Raw
        amount is retained in the fact for audit but is not used as the KPI.
        """
        lakehouse = excel_lakehouse_status()
        fact = lakehouse.get("fact_anggaran", {})
        counts = lakehouse.get("counts", {})
        return jsonify(
            {
                "status": lakehouse.get("status", "missing"),
                "total_anggaran": fact.get("total_anggaran"),
                "jumlah_item": fact.get("jumlah_item") or counts.get("fact_anggaran_rows"),
                "jumlah_iku": fact.get("jumlah_iku"),
                "jumlah_kegiatan": fact.get("jumlah_kegiatan"),
                "status_rekonsiliasi": fact.get("status_rekonsiliasi"),
                "fact_rows": counts.get("fact_anggaran_rows"),
                "source": "excel_lakehouse_gold_fact_anggaran",
                "note": "Total Anggaran dihitung dari SUM(jumlah_weighted_iku).",
            }
        )

    @app.get("/api/superset/assets")
    def superset_assets():
        return jsonify(read_superset_reference())

    @app.get("/api/superset/databases")
    def superset_databases():
        try:
            databases = list_superset_databases()
            return jsonify(
                {"status": "ready", "databases": databases, "count": len(databases)}
            )
        except Exception as exc:
            return jsonify(
                {"status": "unreachable", "databases": [], "message": str(exc)}
            )

    @app.get("/api/superset/dashboards")
    def superset_dashboards():
        try:
            dashboards = list_superset_dashboards()
            return jsonify(
                {"status": "ready", "dashboards": dashboards, "count": len(dashboards)}
            )
        except Exception as exc:
            return jsonify(
                {"status": "unreachable", "dashboards": [], "message": str(exc)}
            )

    @app.get("/api/superset/chart-data")
    def superset_chart_data():
        limit = request.args.get("limit", 100, type=int)
        frame, metadata = fetch_superset_fact_rows(limit=limit)
        if frame is None:
            return jsonify({**metadata, "data": None}), 503
        return jsonify(
            {
                **metadata,
                "row_count": int(len(frame)),
                "columns": list(frame.columns),
                "data": frame.head(max(limit, 1))
                .where(pd.notna(frame), None)
                .to_dict(orient="records"),
            }
        )

    @app.get("/api/runtime-config")
    def runtime_config():
        return jsonify(
            {
                "target_prodi": "Sains Data",
                "target_fakultas": "Fakultas Sains",
                "target_tahun_anggaran": "2025",
                "paths": {
                    "raw_rab": relative_path(raw_rab_path()),
                },
            }
        )

    @app.get("/api/runtime-context")
    def runtime_context_get():
        payload = (
            read_json(OUTPUTS_DIR / "reports" / "active_runtime_context.json") or {}
        )
        base = runtime_config().get_json()
        return jsonify(
            {
                **base,
                "context": payload.get("context") or {},
                "readiness": payload.get("readiness") or {},
            }
        )

    @app.post("/api/runtime-context")
    def runtime_context_post():
        context = request.get_json(silent=True) or {}
        required = ["target_prodi", "target_tahun_anggaran"]
        missing = [key for key in required if not str(context.get(key) or "").strip()]
        readiness = {
            "context_ready": not missing,
            "missing": missing,
            "message": "Konteks upload siap dipakai pipeline."
            if not missing
            else "Lengkapi konteks upload sebelum menjalankan pipeline.",
        }
        payload = {
            "status": "success",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "context": context,
            "readiness": readiness,
        }
        path = OUTPUTS_DIR / "reports" / "active_runtime_context.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return jsonify(payload)

    @app.get("/api/status/services")
    def status_services():
        return jsonify(service_statuses())

    @app.get("/api/data/source-status")
    def data_source_status():
        truth = build_system_truth_status(write_outputs=False)
        return jsonify(
            {"excel_lakehouse": truth.get("sources", {}).get("excel_lakehouse")}
        )

    @app.get("/api/metrics")
    def metrics():
        return jsonify(metrics_payload())

    @app.get("/api/system-truth/status")
    def system_truth_status():
        return jsonify(build_system_truth_status(write_outputs=True))

    @app.get("/api/activity")
    @app.get("/api/activity/recent")
    def activity():
        return jsonify(read_activities())

    @app.post("/api/airflow/trigger")
    def airflow_trigger():
        payload = request.get_json(silent=True) or {}
        active_dataset = excel_upload.normalize_dataset_file_kinds(
            read_json(excel_upload.ACTIVE_EXCEL_DATASET_PATH) or {}
        )
        session_id = str(
            payload.get("dataset_session_id")
            or active_dataset.get("dataset_session_id")
            or active_dataset.get("dataset_id")
            or "local_session"
        ).strip()
        requested_run_id = str(payload.get("pipeline_run_id") or "").strip()

        with _airflow_trigger_lock:
            try:
                validation = validate_committed_dataset(active_dataset, PORTAL_DIR.parent)
                if active_dataset and not validation.get("valid"):
                    return jsonify({"status": "failed", "message": "Dataset aktif belum valid.", "errors": validation.get("errors", [])}), 400
                # Remove abandoned queued runs created for an older dataset session
                # so they cannot execute later against a newer active dataset and
                # fail the pipeline guard. Keeps the Airflow queue single-purpose.
                try:
                    purged = purge_stale_queued_runs(session_id)
                    if purged:
                        append_activity(
                            action="purge_stale_runs",
                            source="airflow",
                            status="success",
                            message=f"Menghapus {len(purged)} run Airflow antrean yang sudah tidak berlaku.",
                            target=",".join(purged[:5]),
                        )
                except RuntimeError:
                    pass
                # Airflow membatasi DAG ini ke satu active run. Reuse a queued or
                # running run for this exact dataset session so retries/tabs cannot
                # create another queued run. Runs for other (stale) sessions are
                # never reused; they fail the pipeline guard and block the queue.
                try:
                    active = get_active_dag_run(dataset_session_id=session_id)
                except RuntimeError:
                    # A transient list failure must not turn a valid trigger into
                    # a local fallback; Airflow POST remains the source of truth.
                    active = None
                if active:
                    return jsonify(
                        {
                            "status": "success",
                            "mode": "airflow",
                            "deduplicated": True,
                            "message": "Pipeline untuk dataset ini sedang berjalan.",
                            **active,
                        }
                    )

                run_id = requested_run_id or create_pipeline_run_id()
                res = trigger_dag(
                    dataset_session_id=session_id,
                    pipeline_run_id=run_id,
                    dashboard_mode=active_dataset.get("dashboard_mode") or "update",
                    dashboard_database_id=active_dataset.get("dashboard_database_id"),
                    dashboard_dashboard_id=active_dataset.get("dashboard_dashboard_id"),
                )
                append_activity(
                    action="trigger_dag",
                    source="airflow",
                    status=res.get("state", "queued"),
                    message=f"DAG Airflow dipicu: {res.get('dag_run_id')}",
                    target=str(res.get("dag_run_id", "")),
                )
                return jsonify(
                    {
                        "status": "success",
                        "mode": "airflow",
                        "deduplicated": False,
                        "loading": True,
                        **res,
                    }
                ), 202
            except Exception as exc:
                return jsonify(
                    {
                        "status": "failed",
                        "mode": "airflow",
                        "loading": False,
                        "message": f"Airflow tidak dapat menjalankan pipeline: {exc}",
                    }
                ), 503

    @app.get("/api/airflow/active")
    def airflow_active():
        try:
            run = get_active_dag_run()
            return jsonify(
                {"status": "ready" if run else "idle", "active": bool(run), "run": run}
            )
        except Exception as exc:
            return jsonify(
                {"status": "unreachable", "active": False, "message": str(exc)}
            )

    @app.get("/api/airflow/latest")
    def airflow_latest():
        try:
            run = get_latest_dag_run()
            return jsonify({"status": "ready" if run else "idle", "run": run})
        except Exception as exc:
            truth = build_system_truth_status(write_outputs=False)
            return jsonify(
                {
                    "status": "unreachable",
                    "message": str(exc),
                    "fallback_generated_at": truth.get("generated_at"),
                }
            )

    @app.get("/api/airflow/runtime")
    def airflow_runtime():
        try:
            return _no_store_json(get_runtime_snapshot())
        except Exception as exc:
            return _no_store_json(
                {
                    "status": "unreachable",
                    "active": False,
                    "active_run": None,
                    "latest_run": None,
                    "runtime_run": None,
                    "source": "none",
                    "message": str(exc),
                }
            )

    @app.get("/api/airflow/runs")
    @app.get("/api/airflow/runs/<run_id>")
    def airflow_runs(run_id=None):
        if run_id:
            try:
                run = get_dag_run(run_id)
                dataset_status = None
                if run.get("state") in {"failed", "upstream_failed"}:
                    active_path = excel_upload.ACTIVE_EXCEL_DATASET_PATH
                    active = read_json(active_path) or {}
                    if active.get("dataset_session_id") == (run.get("conf") or {}).get("dataset_session_id"):
                        active = {**active, "status": "failed", "upload_state": "FAILED"}
                        active_path.write_text(json.dumps(active, indent=2, ensure_ascii=False), encoding="utf-8")
                        dataset_status = "failed"
                return jsonify({"status": "failed" if dataset_status else "success", "run": run, "dataset_status": dataset_status})
            except Exception as exc:
                return jsonify({"status": "not_found", "message": str(exc)}), 404
        try:
            runs = get_all_dag_runs(limit=10)
            return jsonify({"status": "success", "runs": runs})
        except Exception as exc:
            return jsonify({"status": "unreachable", "runs": [], "message": str(exc)})

    @app.get("/api/lakehouse/summary")
    def lakehouse():
        return jsonify(lakehouse_summary())

    @app.get("/api/excel-lakehouse/status")
    def excel_lakehouse_status_endpoint():
        return jsonify(excel_lakehouse_status())

    @app.get("/api/upload/session/status")
    def upload_session_status():
        active = excel_upload.normalize_dataset_file_kinds(
            read_json(excel_upload.ACTIVE_EXCEL_DATASET_PATH)
        )
        registry = read_json(excel_upload.EXCEL_DATASET_REGISTRY_PATH)
        staging_dir = excel_upload.DATA_DIR / "uploads" / "staging"
        staging_files = (
            sorted(path for path in staging_dir.rglob("*") if path.is_file() and path.name != ".gitkeep")
            if staging_dir.exists()
            else []
        )
        active_files = active.get("files", []) if isinstance(active, dict) else []
        committed_files = [
            item
            for item in active_files
            if item.get("path") and (PORTAL_DIR.parent / str(item["path"])).exists()
        ]
        has_active = bool(active_files)
        return jsonify(
            {
                "status": "committed" if committed_files else "empty",
                "source": _safe_relative_path(excel_upload.ACTIVE_EXCEL_DATASET_PATH)
                if has_active
                else None,
                "registry_source": _safe_relative_path(
                    excel_upload.EXCEL_DATASET_REGISTRY_PATH
                )
                if registry and not registry.get("_error")
                else None,
                "active_dataset_id": active.get("dataset_id")
                if isinstance(active, dict)
                else None,
                "dataset_session_id": active.get("dataset_session_id")
                if isinstance(active, dict)
                else None,
                "upload_mode": active.get("upload_mode")
                if isinstance(active, dict)
                else None,
                "metadata_scope": active.get("metadata_scope")
                if isinstance(active, dict)
                else None,
                "committed_file_count": len(committed_files),
                "files": committed_files,
                "staging_file_count": len(staging_files),
                "staging_status": "has_files" if staging_files else "empty",
                "message": "Dataset Excel aktif tersedia di Raw."
                if committed_files
                else "Belum ada upload session aktif yang sudah commit.",
            }
        )

    @app.get("/api/storage/manifest")
    def storage_manifest():
        payload = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        return jsonify(
            payload
            or {"available": False, "message": "Storage manifest belum tersedia."}
        )

    @app.get("/api/reports/bab4-evidence")
    def bab4_evidence():
        payload = read_json(OUTPUTS_DIR / "reports" / "bab4_evidence_summary.json")
        return jsonify(
            payload
            or {"available": False, "message": "Ringkasan bukti Bab 4 belum tersedia."}
        )

    @app.get("/api/data/preview")
    @app.get("/api/preview/<layer>")
    def data_preview(layer=None):
        if layer is None:
            layer = request.args.get("layer", "gold")
        filename = request.args.get("file")
        limit = request.args.get("limit", 10, type=int)
        path = resolve_preview_file(layer, filename)
        if path is None:
            return jsonify(
                {
                    "available": False,
                    "message": f"Layer '{layer}' tidak valid.",
                    "columns": [],
                    "rows": [],
                    "limit": limit,
                }
            ), 404
        payload = csv_preview(path, limit=limit)
        status_code = 200 if payload["available"] else 404
        return jsonify(payload), status_code

    @app.get("/api/data/rejected-rows")
    def rejected_rows():
        payload = csv_preview(
            PORTAL_DIR.parent / "data" / "quarantine" / "logs" / "rejected_rows.csv",
            limit=request.args.get("limit", 25, type=int),
        )
        if not payload["available"]:
            payload["message"] = "Rejected rows belum tersedia."
            return jsonify(payload), 200
        return jsonify(payload)

    @app.post("/api/upload/excel-lakehouse")
    def upload_excel_lakehouse():
        try:
            result = commit_excel_lakehouse_dataset(request.form, request.files)
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="upload_excel_lakehouse",
            source="upload",
            status="success",
            target=result.get("dataset_id", ""),
            message="Dataset Excel-only berhasil di-commit ke raw Excel lakehouse.",
        )
        return jsonify(result)

    @app.post("/api/upload/excel-dataset")
    def upload_excel_dataset():
        return upload_excel_lakehouse()

    @app.delete("/api/upload/session/file")
    def delete_upload_session_file():
        payload = request.get_json(silent=True) or {}
        try:
            result = excel_upload.delete_active_dataset_file(payload.get("filename"))
        except FileNotFoundError as exc:
            return jsonify({"status": "not_found", "message": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="delete_upload_file",
            source="upload",
            status="success",
            target=result.get("deleted_file", {}).get("filename", ""),
            message="Satu file dihapus dari dataset aktif dan Raw.",
        )
        return _no_store_json(result)

    @app.delete("/api/upload/session")
    def delete_upload_session():
        try:
            result = excel_upload.delete_all_active_dataset_files()
        except FileNotFoundError as exc:
            return jsonify({"status": "not_found", "message": str(exc)}), 404
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="delete_upload_dataset",
            source="upload",
            status="success",
            target=result.get("deleted_dataset_id") or "active-dataset",
            message="Seluruh file dataset aktif dihapus dari Raw.",
        )
        return _no_store_json(result)

    @app.get("/api/datasets")
    def datasets():
        payload = read_json(OUTPUTS_DIR / "reports" / "excel_dataset_registry.json")
        return jsonify(payload or {"active_dataset_id": None, "datasets": []})

    @app.get("/api/pipeline/status/<run_id>")
    def pipeline_status_run(run_id: str):
        status = excel_lakehouse_status()
        summary = read_json(OUTPUTS_DIR / "reports" / "pipeline_run_summary.json") or {}
        return jsonify(
            {
                "run_id": run_id,
                "status": status.get("status"),
                "summary": summary,
                "artifacts": status.get("artifacts"),
            }
        )

    @app.post("/api/pipeline/run/<run_id>")
    def pipeline_run_id(run_id: str):
        active = read_json(excel_upload.ACTIVE_EXCEL_DATASET_PATH) or {}
        dataset_session_id = active.get("dataset_session_id") or active.get(
            "dataset_id"
        )
        if active.get("status") != "committed" or not dataset_session_id:
            return jsonify(
                {
                    "status": "failed",
                    "message": "Dataset aktif COMMITTED tidak tersedia.",
                }
            ), 400
        env_overrides = {
            "PIPELINE_RUN_ID": run_id,
            "DATASET_SESSION_ID": str(dataset_session_id),
        }
        result = run_command_group("excel-lakehouse", env_overrides=env_overrides)
        count_result = (
            run_command_group("excel-count-validation", env_overrides=env_overrides)
            if result.get("status") == "success"
            else None
        )
        storage_result = (
            run_command_group("excel-storage-manifest", env_overrides=env_overrides)
            if result.get("status") == "success"
            else None
        )
        return jsonify(
            {
                "run_id": run_id,
                "pipeline": result,
                "count_validation": count_result,
                "storage_manifest": storage_result,
            }
        ), 200 if result.get("status") == "success" else 500

    @app.get("/api/storage/manifest/<run_id>")
    def storage_manifest_run(run_id: str):
        payload = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        return jsonify(
            payload or {"run_id": run_id, "status": "missing", "entries": []}
        )

    @app.get("/api/data-quality/<run_id>")
    def data_quality_run(run_id: str):
        payload = read_json(OUTPUTS_DIR / "reports" / "pipeline_count_validation.json")
        return jsonify(payload or {"run_id": run_id, "status": "missing"})

    @app.get("/api/iku-review/queue")
    def iku_review_queue_endpoint():
        return jsonify(iku_review_queue(limit=request.args.get("limit", 100, type=int)))

    @app.get("/api/mapping-review/queue")
    def mapping_review_queue_endpoint():
        return jsonify(
            mapping_review_queue(limit=request.args.get("limit", 100, type=int))
        )

    @app.post("/api/iku-review/override")
    def iku_review_override_endpoint():
        try:
            return jsonify(save_iku_override(request.get_json(silent=True) or {}))
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400

    @app.get("/api/dashboard/links/<run_id>")
    def dashboard_links_run(run_id: str):
        payload = read_json(
            OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json"
        ) or read_json(OUTPUTS_DIR / "reports" / "superset_excel_assets.json")
        return jsonify(
            payload or {"run_id": run_id, "status": "missing", "dashboard_url": None}
        )

    @app.get("/api/local-dashboard/status")
    def local_dashboard_status():
        return jsonify(dashboard_section(request.args, "status"))

    @app.get("/api/local-dashboard/filters")
    def local_dashboard_filters():
        return jsonify(dashboard_section(request.args, "filters"))

    @app.get("/api/local-dashboard/summary")
    def local_dashboard_summary():
        return jsonify(dashboard_section(request.args, "summary"))

    @app.get("/api/local-dashboard/charts")
    def local_dashboard_charts():
        return jsonify(dashboard_section(request.args, "charts"))

    @app.get("/api/local-dashboard/table")
    def local_dashboard_table():
        return jsonify(dashboard_section(request.args, "table"))

    @app.get("/api/local-dashboard/all")
    def local_dashboard_all():
        payload = dashboard_section(request.args, "all")
        write_dashboard_reports()
        return jsonify(payload)

    @app.post("/api/pipeline/<name>")
    def pipeline(name: str):
        if name == "full-run-basic":
            result = run_full("local-basic")
            return jsonify(result), 200 if result.get("status") == "success" else 500
        if name == "full-run":
            payload = request.get_json(silent=True) or {}
            return jsonify(run_full(payload.get("mode", "local-basic")))
        mapping = {
            "quality-gate": "quality-gate",
            "bronze": "bronze",
            "silver": "silver",
            "gold": "gold",
            "excel-lakehouse": "excel-lakehouse",
            "superset-excel": "superset-excel",
            "metrics": "metrics",
            "excel-storage-manifest": "excel-storage-manifest",
            "excel-count-validation": "excel-count-validation",
            "load-gold-postgres": "load-gold-postgres",
            "validate-gold": "validate-gold",
        }
        command = mapping.get(name)
        if command is None:
            return jsonify(
                {"status": "failed", "message": "Endpoint pipeline tidak dikenal."}
            ), 404
        payload = request.get_json(silent=True) or {}
        env_overrides = {
            key: str(value)
            for key, value in {
                "DATASET_SESSION_ID": payload.get("dataset_session_id"),
                "PIPELINE_RUN_ID": payload.get("pipeline_run_id"),
                "AIRFLOW_DAG_RUN_ID": payload.get("airflow_dag_run_id"),
            }.items()
            if value
        }
        result = run_command_group(command, env_overrides=env_overrides)
        return jsonify(result), 200 if result["status"] == "success" else 500

    @app.get("/api/uat/summary")
    def uat_summary():
        return jsonify(build_system_truth_status(write_outputs=True).get("uat"))

    @app.post("/api/uat/submit")
    def uat_submit():
        payload = request.get_json(silent=True) or {}
        report_path = OUTPUTS_DIR / "reports" / "uat_local_submissions.json"
        existing = read_json(report_path) or {"status": "available", "items": []}
        item = {
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "mode": payload.get("mode") or "local_feedback",
            "evaluator": payload.get("evaluator"),
            "module": payload.get("module"),
            "scores": payload.get("scores") or [],
            "feedback": payload.get("feedback"),
            "time_label": payload.get("time"),
        }
        items = [item, *(existing.get("items") or [])][:250]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "status": "available",
                    "generated_at": item["submitted_at"],
                    "items": items,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        append_activity(
            "uat_submit",
            "analytics",
            "success",
            "Evaluasi UAT lokal diterima.",
            "outputs/uat",
        )
        return jsonify(
            {
                "status": "success",
                "message": "Evaluasi UAT lokal diterima.",
                "item": item,
            }
        )

    @app.post("/api/system/shutdown")
    def system_shutdown_endpoint():
        append_activity(
            "system_shutdown",
            "system",
            "failed",
            "Penghentian layanan container tidak tersedia pada backend lokal.",
            "outputs/logs",
        )
        return jsonify(
            {
                "status": "not_implemented",
                "message": "Penghentian layanan container belum diimplementasikan pada backend lokal.",
            }
        ), 501

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("PORTAL_BACKEND_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORTAL_BACKEND_BIND_PORT", "8091")),
        debug=False,
    )
