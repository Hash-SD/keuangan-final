from __future__ import annotations

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .services.activity import append_activity, read_activities
from .services.files import csv_preview, read_json, relative_path, resolve_preview_file
from .services.excel_lakehouse import excel_lakehouse_status
from .services.excel_upload import commit_excel_lakehouse_dataset
from .services.iku_review import iku_review_queue, mapping_review_queue, save_iku_override
from .services.lakehouse import lakehouse_summary
from .services.metrics import metrics_payload
from .services.paths import OUTPUTS_DIR, PORTAL_DIR
from .services.pipeline import run_command_group, run_full
from .services.system_status import service_statuses
from src.common.runtime_paths import raw_rab_path
from src.status.system_truth_status import build_system_truth_status


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(PORTAL_DIR), static_url_path="")
    max_upload_mb = int(os.getenv("PORTAL_MAX_UPLOAD_MB", "100"))
    app.config["MAX_CONTENT_LENGTH"] = max_upload_mb * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"status": "failed", "message": f"Ukuran file melebihi batas {max_upload_mb} MB."}), 413

    @app.get("/")
    def index():
        return send_from_directory(PORTAL_DIR, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "portal-backend", "mode": "local-on-premise", "basis": "excel_lakehouse_fact_anggaran"})

    @app.get("/api/readiness")
    def readiness():
        checks = {}
        for name, path in {
            "outputs_reports": OUTPUTS_DIR / "reports",
            "raw_excel_lakehouse": PORTAL_DIR.parent / "data" / "raw" / "excel_lakehouse",
        }.items():
            checks[name] = {"status": "ready" if path.exists() else "missing", "path": relative_path(path)}
        truth = build_system_truth_status(write_outputs=False)
        manifest = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        checks["system_truth"] = {"status": "ready", "generated_at": truth.get("generated_at")}
        checks["storage_manifest"] = {"status": "ready" if manifest and not manifest.get("_error") else "missing", "source": "outputs/reports/storage_manifest.json"}
        checks["superset"] = truth.get("services", {}).get("superset", {"status": "unreachable"})
        ready = all(item.get("status") in {"ready", "empty", "skipped", "mapped", "configured", "unreachable"} for item in checks.values())
        return jsonify({"status": "ready" if ready else "not_ready", "checks": checks})

    @app.get("/api/superset/status")
    def superset_status():
        truth = build_system_truth_status(write_outputs=False)
        return jsonify(
            {
                "service": truth.get("services", {}).get("superset", {"status": "unreachable"}),
                "dashboard": truth.get("dashboard", {"status": "not_started"}),
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
        return runtime_config()

    @app.post("/api/runtime-context")
    def runtime_context_post():
        return jsonify({"status": "success", "context": (request.get_json(silent=True) or {})})

    @app.get("/api/status/services")
    def status_services():
        return jsonify(service_statuses())

    @app.get("/api/data/source-status")
    def data_source_status():
        truth = build_system_truth_status(write_outputs=False)
        return jsonify({"excel_lakehouse": truth.get("sources", {}).get("excel_lakehouse")})

    @app.get("/api/metrics")
    def metrics():
        return jsonify(metrics_payload())

    @app.get("/api/system-truth/status")
    def system_truth_status():
        return jsonify(build_system_truth_status(write_outputs=True))

    @app.get("/api/activity")
    def activity():
        return jsonify(read_activities())

    @app.get("/api/lakehouse/summary")
    def lakehouse():
        return jsonify(lakehouse_summary())

    @app.get("/api/excel-lakehouse/status")
    def excel_lakehouse_status_endpoint():
        return jsonify(excel_lakehouse_status())

    @app.get("/api/storage/manifest")
    def storage_manifest():
        payload = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        return jsonify(payload or {"available": False, "message": "Storage manifest belum tersedia."})

    @app.get("/api/reports/bab4-evidence")
    def bab4_evidence():
        payload = read_json(OUTPUTS_DIR / "reports" / "bab4_evidence_summary.json")
        return jsonify(payload or {"available": False, "message": "Ringkasan bukti Bab 4 belum tersedia."})

    @app.get("/api/data/preview")
    def data_preview():
        layer = request.args.get("layer", "gold")
        filename = request.args.get("file")
        limit = request.args.get("limit", 10, type=int)
        path = resolve_preview_file(layer, filename)
        if path is None:
            return jsonify({"available": False, "message": "Layer atau file tidak valid.", "columns": [], "rows": [], "limit": limit}), 404
        payload = csv_preview(path, limit=limit)
        status_code = 200 if payload["available"] else 404
        return jsonify(payload), status_code

    @app.get("/api/data/rejected-rows")
    def rejected_rows():
        payload = csv_preview(PORTAL_DIR.parent / "data" / "quarantine" / "logs" / "rejected_rows.csv", limit=request.args.get("limit", 25, type=int))
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

    @app.get("/api/datasets")
    def datasets():
        payload = read_json(OUTPUTS_DIR / "reports" / "excel_dataset_registry.json")
        return jsonify(payload or {"active_dataset_id": None, "datasets": []})

    @app.get("/api/pipeline/status/<run_id>")
    def pipeline_status_run(run_id: str):
        status = excel_lakehouse_status()
        summary = read_json(OUTPUTS_DIR / "reports" / "pipeline_run_summary.json") or {}
        return jsonify({"run_id": run_id, "status": status.get("status"), "summary": summary, "artifacts": status.get("artifacts")})

    @app.post("/api/pipeline/run/<run_id>")
    def pipeline_run_id(run_id: str):
        result = run_command_group("excel-lakehouse")
        count_result = run_command_group("excel-count-validation") if result.get("status") == "success" else None
        storage_result = run_command_group("excel-storage-manifest") if result.get("status") == "success" else None
        return jsonify({"run_id": run_id, "pipeline": result, "count_validation": count_result, "storage_manifest": storage_result}), 200 if result.get("status") == "success" else 500

    @app.get("/api/storage/manifest/<run_id>")
    def storage_manifest_run(run_id: str):
        payload = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        return jsonify(payload or {"run_id": run_id, "status": "missing", "entries": []})

    @app.get("/api/data-quality/<run_id>")
    def data_quality_run(run_id: str):
        payload = read_json(OUTPUTS_DIR / "reports" / "pipeline_count_validation.json")
        return jsonify(payload or {"run_id": run_id, "status": "missing"})

    @app.get("/api/iku-review/queue")
    def iku_review_queue_endpoint():
        return jsonify(iku_review_queue(limit=request.args.get("limit", 100, type=int)))

    @app.get("/api/mapping-review/queue")
    def mapping_review_queue_endpoint():
        return jsonify(mapping_review_queue(limit=request.args.get("limit", 100, type=int)))

    @app.post("/api/iku-review/override")
    def iku_review_override_endpoint():
        try:
            return jsonify(save_iku_override(request.get_json(silent=True) or {}))
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400

    @app.get("/api/dashboard/links/<run_id>")
    def dashboard_links_run(run_id: str):
        payload = read_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json") or read_json(OUTPUTS_DIR / "reports" / "superset_excel_assets.json")
        return jsonify(payload or {"run_id": run_id, "status": "missing", "dashboard_url": None})

    @app.post("/api/pipeline/<name>")
    def pipeline(name: str):
        if name == "full-run-basic":
            return jsonify(run_full("local-basic"))
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
            "validate-gold": "validate-gold",
        }
        command = mapping.get(name)
        if command is None:
            return jsonify({"status": "failed", "message": "Endpoint pipeline tidak dikenal."}), 404
        result = run_command_group(command)
        return jsonify(result), 200 if result["status"] == "success" else 500

    @app.get("/api/uat/summary")
    def uat_summary():
        return jsonify(build_system_truth_status(write_outputs=True).get("uat"))

    @app.post("/api/uat/submit")
    def uat_submit():
        append_activity("uat_submit", "analytics", "success", "Evaluasi UAT lokal diterima.", "outputs/uat")
        return jsonify({"status": "success", "message": "Evaluasi UAT lokal diterima."})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("PORTAL_BACKEND_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORTAL_BACKEND_BIND_PORT", "8091")),
        debug=False,
    )
