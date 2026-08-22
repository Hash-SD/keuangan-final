from __future__ import annotations

import os
import sys
import json
from urllib.request import Request, urlopen
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from _shared import (  # noqa: E402
    fetch_chart_data,
    fetch_dashboard_meta,
    fetch_dashboards,
    parse_filter_query,
    superset_base_url,
)

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
PORTAL_BACKEND_URL = os.getenv("PORTAL_BACKEND_URL", "http://localhost:8091").rstrip("/")


def fetch_active_dashboard_status() -> dict:
    """Read the portal's active-data truth without touching Superset data."""

    last_error: Exception | None = None
    candidates = [PORTAL_BACKEND_URL]
    if PORTAL_BACKEND_URL != "http://portal-backend:8091":
        candidates.append("http://portal-backend:8091")
    if PORTAL_BACKEND_URL != "http://localhost:8091":
        candidates.append("http://localhost:8091")
    for base_url in candidates:
        try:
            request = Request(f"{base_url}/api/system-truth/status", method="GET")
            with urlopen(request, timeout=2) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    else:
        raise RuntimeError("Portal backend tidak dapat dijangkau.") from last_error
    dashboard = payload.get("dashboard") if isinstance(payload, dict) else None
    if not isinstance(dashboard, dict):
        return {"status": "unknown", "message": "Status dataset aktif belum tersedia."}
    return {
        "status": dashboard.get("status") or "unknown",
        "scope": dashboard.get("scope"),
        "message": dashboard.get("message") or "Status dataset aktif belum tersedia.",
        "dataset_session_id": dashboard.get("dataset_session_id"),
        "pipeline_run_id": dashboard.get("pipeline_run_id"),
    }


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    @app.get("/")
    def index():
        return send_from_directory(PUBLIC_DIR, "index.html")

    @app.get("/<path:filename>")
    def assets(filename: str):
        return send_from_directory(PUBLIC_DIR, filename)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "superset-dashboard", "source": "superset_api", "superset_base": superset_base_url()})

    @app.get("/api/dashboards")
    def dashboards():
        try:
            return jsonify({"dashboards": fetch_dashboards()})
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "unreachable", "error": str(exc)}), 502

    @app.get("/api/active-status")
    def active_status():
        try:
            return jsonify(fetch_active_dashboard_status())
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "unknown", "message": "Status dataset aktif tidak dapat diperiksa.", "error": str(exc)}), 200

    @app.get("/api/dashboard/<int:dashboard_id>/meta")
    def dashboard_meta(dashboard_id: int):
        try:
            return jsonify(fetch_dashboard_meta(dashboard_id))
        except Exception as exc:  # noqa: BLE001
            return jsonify({"status": "unreachable", "error": str(exc), "dashboard_id": dashboard_id}), 502

    @app.get("/api/chart/<int:chart_id>/data")
    def chart_data(chart_id: int):
        year = request.args.get("tahun") or None
        if year is not None and year.strip() == "":
            year = None
        refresh = request.args.get("refresh") in ("1", "true", "yes")
        dashboard_id = request.args.get("dashboard")
        try:
            dashboard_id = int(dashboard_id) if dashboard_id else None
        except ValueError:
            dashboard_id = None
        try:
            cross_filters = parse_filter_query(request.args.get("filters"))
        except ValueError as exc:
            return jsonify({"status": "error", "error": str(exc), "chart_id": chart_id}), 400
        payload = fetch_chart_data(
            chart_id,
            year,
            dashboard_id=dashboard_id,
            refresh=refresh,
            cross_filters=cross_filters,
        )
        status_code = 200 if payload.get("status") in ("success", "error") else 502
        return jsonify(payload), status_code

    @app.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.getenv("SUPERSET_DASHBOARD_BIND_HOST", "0.0.0.0"),
        port=int(os.getenv("SUPERSET_DASHBOARD_BIND_PORT", "8092")),
        debug=False,
    )
