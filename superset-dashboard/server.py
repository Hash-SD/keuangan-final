from __future__ import annotations

import os
import sys
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

from _shared import (  # noqa: E402
    fetch_chart_data,
    fetch_dashboard_meta,
    fetch_dashboards,
    superset_base_url,
)

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"


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
        payload = fetch_chart_data(chart_id, year, dashboard_id=dashboard_id, refresh=refresh)
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
