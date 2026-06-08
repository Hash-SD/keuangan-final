from __future__ import annotations

import os
import shutil

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .services.activity import append_activity, read_activities
from .services.files import csv_preview, read_json, record_upload, relative_path, resolve_preview_file, save_upload, update_active_upload_context
from .services.lakehouse import lakehouse_summary
from .services.metrics import metrics_payload
from .services.paths import OUTPUTS_DIR, PORTAL_DIR
from .services.pipeline import run_command_group, run_full
from .services.reference import pdf_sample_status, reference_spi_preview, reference_summary, reference_ukt_preview, source_status
from .services.runtime_context import (
    context_from_form,
    infer_context_from_csv,
    infer_context_from_excel,
    period_metadata,
    read_active_context,
    scenario_manifest,
    write_active_context,
)
from .services.system_status import service_statuses
from src.common.runtime_paths import raw_pdf_path, raw_rab_path, sample_pdf_path, silver_rab_path
from src.status.system_truth_status import build_system_truth_status


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
        context = read_active_context()
        return jsonify(
            {
                **context,
                "paths": {
                    "raw_pdf": relative_path(raw_pdf_path()),
                    "sample_pdf": relative_path(sample_pdf_path()),
                    "raw_rab": relative_path(raw_rab_path()),
                    "silver_rab": relative_path(silver_rab_path()),
                },
            }
        )

    @app.get("/api/runtime-context")
    def runtime_context_get():
        return jsonify(read_active_context())

    @app.post("/api/runtime-context")
    def runtime_context_post():
        payload = request.get_json(silent=True) or request.form
        context = write_active_context(payload, source="manual")
        append_activity(
            action="set_runtime_context",
            source="runtime_context",
            status="success",
            target=context["target_label"],
            message=f"Konteks aktif diubah ke {context['target_label']}.",
        )
        return jsonify({"status": "success", "context": context})

    @app.get("/api/upload/scenarios")
    def upload_scenarios():
        return jsonify({"scenarios": scenario_manifest()})

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

    @app.get("/api/system-truth/status")
    def system_truth_status():
        return jsonify(build_system_truth_status(write_outputs=True))

    @app.get("/api/activity")
    def activity():
        return jsonify(read_activities())

    @app.get("/api/lakehouse/summary")
    def lakehouse():
        return jsonify(lakehouse_summary())

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

    def _upload(upload_type: str, allowed_extensions: set[str]):
        uploads = request.files.getlist("file")
        if not uploads:
            return jsonify({"status": "failed", "message": "Field file wajib diisi."}), 400
        if upload_type != "csv" and len(uploads) > 1:
            return jsonify({"status": "failed", "message": "PDF dan Excel hanya menerima satu file per upload."}), 400

        context = context_from_form(request.form) or read_active_context()
        context = write_active_context(context, source="upload_form")
        results = [save_upload(uploaded, upload_type, allowed_extensions, period=period_metadata(context)) for uploaded in uploads]
        for item in results:
            if item.get("status") != "success" or not item.get("path"):
                continue
            source_path = PORTAL_DIR.parent / item["path"]
            canonical = raw_pdf_path() if upload_type == "pdf" else raw_rab_path() if upload_type == "excel" else None
            if canonical is not None:
                canonical.parent.mkdir(parents=True, exist_ok=True)
                if source_path.resolve() != canonical.resolve():
                    shutil.copyfile(source_path, canonical)
                item["canonical_path"] = relative_path(canonical)
                record_upload(item)
        failed = [item for item in results if item["status"] != "success"]
        successful_paths = [PORTAL_DIR.parent / item["path"] for item in results if item["status"] == "success" and item.get("path")]
        inferred_context = None
        try:
            if upload_type == "csv":
                inferred_context = infer_context_from_csv(successful_paths, base=context)
            elif upload_type == "excel" and successful_paths:
                inferred_context = infer_context_from_excel(successful_paths[0], base=context)
            if inferred_context is not None:
                context = write_active_context(inferred_context, source=inferred_context.get("source", "inferred_upload"))
                period = period_metadata(context)
                update_active_upload_context(period)
                for item in results:
                    if item.get("status") == "success":
                        item.update(period)
                        record_upload(item)
        except Exception as exc:
            append_activity("infer_runtime_context", "upload", "failed", f"Gagal membaca konteks dari file upload: {exc}", "runtime_context")
        if len(results) == 1:
            result = results[0]
        else:
            successful = [item for item in results if item["status"] == "success"]
            result = {
                "status": "failed" if failed else "success",
                "type": upload_type,
                "files": successful,
                "failed_files": failed,
                "message": (
                    f"{len(successful)} file {upload_type} berhasil diupload."
                    if not failed
                    else f"{len(failed)} dari {len(results)} file {upload_type} gagal diupload."
                ),
            }
        result["context"] = context
        status_code = 200 if result["status"] == "success" else 400
        append_activity(
            action=f"upload_{upload_type}",
            source="upload",
            status=result["status"],
            target=result.get("path", "") or ", ".join(item.get("path", "") for item in result.get("files", [])),
            message=result.get("message", f"Upload {upload_type} {result['status']} untuk {result.get('target_label', 'periode aktif')}."),
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
            "storage-manifest": "storage-manifest",
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
