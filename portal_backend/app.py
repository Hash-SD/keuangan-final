from __future__ import annotations

import os
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .services.activity import append_activity, read_activities
from .services.files import csv_preview, read_json, relative_path, resolve_preview_file
from .services.lakehouse import lakehouse_summary
from .services.metrics import metrics_payload
from .services.paths import OUTPUTS_DIR, PORTAL_DIR
from .services.pipeline import run_command_group, run_full
from .services.reference import pdf_sample_status, reference_spi_preview, reference_summary, reference_ukt_preview, source_status
from .services.runtime_context import (
    read_active_context,
    scenario_manifest,
    write_active_context,
)
from .services.system_status import service_statuses
from .services.upload_session import commit_session, remove_file, reset_session, session_status, update_context, update_file, update_session
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

    @app.get("/api/readiness")
    def readiness():
        checks = {}
        for name, path in {
            "outputs_reports": OUTPUTS_DIR / "reports",
            "uploads_staging": PORTAL_DIR.parent / "data" / "uploads" / "staging",
            "raw": PORTAL_DIR.parent / "data" / "raw",
        }.items():
            checks[name] = {"status": "ready" if path.exists() else "missing", "path": relative_path(path)}
        upload_status = session_status()
        truth = build_system_truth_status(write_outputs=False)
        manifest = read_json(OUTPUTS_DIR / "reports" / "storage_manifest.json")
        checks["upload_session"] = {"status": "ready", "session_id": upload_status.get("session_id"), "readiness": upload_status.get("readiness")}
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

    @app.get("/api/upload/session/status")
    def upload_session_status():
        return jsonify(session_status())

    @app.post("/api/upload/session")
    def upload_session_post():
        try:
            result = update_session(request.form, request.files)
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="upload_session_stage",
            source="upload",
            status="success",
            target=result.get("session_id", ""),
            message=result.get("message", "File berhasil disimpan di staging."),
        )
        return jsonify(result)

    @app.post("/api/upload/session/context")
    def upload_session_context():
        payload = request.get_json(silent=True) or request.form
        try:
            result = update_context(payload)
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="upload_session_context",
            source="upload",
            status="success",
            target=result.get("session_id", ""),
            message="Konteks periode tersimpan sementara.",
        )
        return jsonify(result)

    @app.post("/api/upload/session/file")
    def upload_session_file():
        upload_type = (request.form.get("upload_type") or "").strip().lower()
        try:
            result = update_file(upload_type, request.files)
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        labels = {"pdf": "PDF", "csv": "CSV", "excel": "Excel"}
        append_activity(
            action="upload_session_file",
            source="upload",
            status="success",
            target=result.get("session_id", ""),
            message=f"{labels.get(upload_type, 'File')} tersimpan sementara di staging.",
        )
        return jsonify(result)

    @app.delete("/api/upload/session/file")
    def upload_session_file_delete():
        payload = request.get_json(silent=True) or {}
        upload_type = str(payload.get("upload_type") or "").strip().lower()
        try:
            result = remove_file(upload_type, filename=payload.get("filename"), file_id=payload.get("file_id"))
        except ValueError as exc:
            return jsonify({"status": "failed", "message": str(exc)}), 400
        append_activity(
            action="upload_session_file_remove",
            source="upload",
            status="success",
            target=result.get("session_id", ""),
            message="File dihapus dari sesi upload.",
        )
        return jsonify(result)

    @app.post("/api/upload/session/commit")
    def upload_session_commit():
        result = commit_session()
        status_code = 200 if result.get("status") == "committed" else 400
        append_activity(
            action="upload_session_commit",
            source="upload",
            status="success" if status_code == 200 else "failed",
            target=result.get("session_id", ""),
            message=result.get("message", "Commit sesi upload diproses."),
        )
        return jsonify(result), status_code

    @app.delete("/api/upload/session/reset")
    def upload_session_reset():
        result = reset_session()
        append_activity("upload_session_reset", "upload", "success", "Sesi upload direset.", result.get("session_id", ""))
        return jsonify(result)

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
        append_activity(
            action=f"upload_{upload_type}_legacy_blocked",
            source="upload",
            status="skipped",
            target="/api/upload/session",
            message="Endpoint upload lama tidak lagi melakukan commit final. Gunakan sesi upload terpadu.",
        )
        return jsonify(
            {
                "status": "failed",
                "message": "Endpoint upload per file sudah dinonaktifkan sebagai alur utama. Gunakan /api/upload/session lalu /api/upload/session/commit.",
                "replacement_endpoint": "/api/upload/session",
                "allowed_extensions": sorted(allowed_extensions),
            }
        ), 410

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
        append_activity("uat_submit", "analytics", "success", "Simulasi UAT dummy diterima; bukan hasil UAT final.", "outputs/uat")
        return jsonify({"status": "success", "message": "Simulasi UAT dummy diterima untuk sesi lokal; bukan hasil UAT final."})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("PORTAL_BACKEND_BIND_HOST", "127.0.0.1"),
        port=int(os.getenv("PORTAL_BACKEND_BIND_PORT", "8091")),
        debug=False,
    )
