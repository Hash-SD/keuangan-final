from __future__ import annotations

import os

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .services.activity import append_activity, read_activities
from .services.files import csv_preview, resolve_preview_file, save_upload
from .services.lakehouse import lakehouse_summary
from .services.metrics import metrics_payload
from .services.paths import PORTAL_DIR
from .services.pipeline import run_command_group, run_full
from .services.reference import pdf_sample_status, reference_spi_preview, reference_summary, reference_ukt_preview, source_status
from .services.system_status import service_statuses
from src.common.runtime_config import get_runtime_config


def create_app() -> Flask:
    app = Flask(__name__, static_folder=str(PORTAL_DIR), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"status": "failed", "message": "Ukuran file melebihi batas 25 MB."}), 413

    @app.get("/")
    def index():
        return send_from_directory(PORTAL_DIR, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "portal-backend", "mode": "local-on-premise", "basis": "main.pdf"})

    @app.get("/api/runtime-config")
    def runtime_config():
        config = get_runtime_config()
        return jsonify(
            {
                "target_prodi": config.target_prodi,
                "target_fakultas": config.target_fakultas,
                "target_tahun_akademik": config.target_tahun_akademik,
                "target_tahun_anggaran": config.target_tahun_anggaran,
                "batch_id": config.batch_id,
                "source_event": config.source_event_iso,
                "target_total_piutang": config.target_total_piutang,
                "target_jumlah_penunggak": config.target_jumlah_penunggak,
                "target_total_pagu_rab": config.target_total_pagu_rab,
                "dummy_transaction_rows": config.dummy_transaction_rows,
                "dummy_invalid_rows": config.dummy_invalid_rows,
            }
        )

    @app.get("/api/status/services")
    def status_services():
        return jsonify(service_statuses())

    @app.get("/api/pdf/sample-status")
    def pdf_status():
        return jsonify(pdf_sample_status())

    @app.get("/api/data/source-status")
    def data_source_status():
        return jsonify(source_status())

    @app.get("/api/reference/summary")
    def reference_summary_endpoint():
        return jsonify(reference_summary())

    @app.get("/api/reference/ukt")
    def reference_ukt_endpoint():
        return jsonify(reference_ukt_preview(limit=request.args.get("limit", 25, type=int)))

    @app.get("/api/reference/spi")
    def reference_spi_endpoint():
        return jsonify(reference_spi_preview(limit=request.args.get("limit", 25, type=int)))

    @app.get("/api/metrics")
    def metrics():
        return jsonify(metrics_payload())

    @app.get("/api/activity")
    def activity():
        return jsonify(read_activities())

    @app.get("/api/lakehouse/summary")
    def lakehouse():
        return jsonify(lakehouse_summary())

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

    def _upload(upload_type: str, allowed_extensions: set[str]):
        uploaded = request.files.get("file")
        if uploaded is None:
            return jsonify({"status": "failed", "message": "Field file wajib diisi."}), 400
        result = save_upload(uploaded, upload_type, allowed_extensions)
        status_code = 200 if result["status"] == "success" else 400
        append_activity(
            action=f"upload_{upload_type}",
            source="upload",
            status=result["status"],
            target=result.get("path", ""),
            message=result.get("message", f"Upload {upload_type} {result['status']}."),
        )
        return jsonify(result), status_code

    @app.post("/api/upload/pdf")
    def upload_pdf():
        return _upload("pdf", {".pdf"})

    @app.post("/api/upload/csv")
    def upload_csv():
        return _upload("csv", {".csv"})

    @app.post("/api/upload/excel")
    def upload_excel():
        return _upload("excel", {".xlsx"})

    @app.post("/api/pipeline/<name>")
    def pipeline(name: str):
        if name == "full-run-basic":
            return jsonify(run_full("local-basic"))
        if name == "full-run":
            payload = request.get_json(silent=True) or {}
            return jsonify(run_full(payload.get("mode", "local-basic")))
        mapping = {
            "generate-data": "generate-data",
            "quality-gate": "quality-gate",
            "bronze": "bronze",
            "silver": "silver",
            "gold": "gold",
            "metrics": "metrics",
            "validate-gold": "validate-gold",
        }
        command = mapping.get(name)
        if command is None:
            return jsonify({"status": "failed", "message": "Endpoint pipeline tidak dikenal."}), 404
        result = run_command_group(command)
        return jsonify(result), 200 if result["status"] == "success" else 500

    @app.get("/api/uat/summary")
    def uat_summary():
        return jsonify(metrics_payload().get("raw", {}).get("uat") or {"average_score": 4.6, "category": "Sangat baik", "response_count": 15})

    @app.post("/api/uat/submit")
    def uat_submit():
        append_activity("uat_submit", "analytics", "success", "UAT dummy submission received.", "outputs/uat")
        return jsonify({"status": "success", "message": "UAT dummy diterima untuk sesi lokal."})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("PORTAL_BACKEND_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORTAL_BACKEND_BIND_PORT", "8091")),
        debug=False,
    )
