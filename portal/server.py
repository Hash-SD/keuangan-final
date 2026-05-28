from __future__ import annotations

import csv
import json
import mimetypes
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


PORT = 8090
PORTAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = PORTAL_DIR.parent


def read_json(relative_path: str):
    path = REPO_ROOT / relative_path
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_error": str(exc)}


def read_csv_preview(relative_path: str, limit: int = 6):
    path = REPO_ROOT / relative_path
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))[:limit]
    except Exception:
        return []


def exists(relative_path: str) -> bool:
    return (REPO_ROOT / relative_path).exists()


def port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def portal_state():
    metrics = {
        "qualityGate": read_json("data/quarantine/logs/quality_gate_summary.json"),
        "reconcile": read_json("outputs/metrics/reconcile_control_total.json"),
        "latency": read_json("outputs/metrics/pipeline_latency.json"),
        "freshness": read_json("outputs/metrics/data_freshness.json"),
        "dropout": read_json("outputs/metrics/dropout_rate.json"),
        "quality": read_json("outputs/metrics/data_quality_score.json"),
        "supersetAssets": read_json("outputs/reports/superset_assets.json"),
        "supersetDashboard": read_json("outputs/reports/superset_dashboard.json"),
        "uat": read_json("outputs/uat/uat_score_summary.json"),
    }
    files = {
        "bronzeMetadata": exists("data/generated/bronze/ingestion_metadata.json"),
        "silverFact": exists("data/generated/silver/fact_piutang_ukt_prodi.csv"),
        "silverTransactions": exists("data/generated/silver/transactions_clean.csv"),
        "silverRab": exists("data/generated/silver/rab_prodi_sains_data_long.csv"),
        "goldFact": exists("data/generated/gold/fact_piutang_ukt_prodi.csv"),
        "goldDashboard": exists("data/generated/gold/vw_dashboard_piutang_ukt.csv"),
        "qualitySummary": exists("data/quarantine/logs/quality_gate_summary.json"),
        "rejectedRows": exists("data/quarantine/logs/rejected_rows.csv"),
    }
    layer_status = {
        "bronzeReady": files["bronzeMetadata"],
        "silverReady": files["silverFact"] and files["silverTransactions"] and files["silverRab"],
        "goldReady": files["goldFact"] and files["goldDashboard"],
        "goldValid": bool(metrics["reconcile"] and str(metrics["reconcile"].get("status", "")).lower() == "pass"),
    }
    services = {
        "portal": True,
        "airflow": port_open("localhost", 8085),
        "superset": port_open("localhost", 8089),
        "minioApi": port_open("localhost", 9000),
        "minioConsole": port_open("localhost", 9001),
        "sparkMaster": port_open("localhost", 8080),
        "sparkWorker": port_open("localhost", 8081),
        "trino": port_open("localhost", 8082),
        "postgres": port_open("localhost", 5432),
    }
    has_metrics = all(
        metrics[key] is not None
        for key in ["reconcile", "latency", "freshness", "dropout", "quality"]
    )
    if not layer_status["goldReady"]:
        dashboard_status = "Waiting for Gold"
    elif not has_metrics:
        dashboard_status = "Waiting for Metrics"
    elif not services["superset"]:
        dashboard_status = "Superset Offline"
    elif not layer_status["goldValid"]:
        dashboard_status = "Validation Failed"
    else:
        dashboard_status = "Ready"

    return {
        "metrics": metrics,
        "files": files,
        "layers": layer_status,
        "services": services,
        "dashboardStatus": dashboard_status,
        "rejectedRows": read_csv_preview("data/quarantine/logs/rejected_rows.csv"),
        "goldPreview": read_csv_preview("data/generated/gold/vw_dashboard_piutang_ukt.csv"),
        "silverPreview": read_csv_preview("data/generated/silver/fact_piutang_ukt_prodi.csv"),
    }


class PortalHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):  # noqa: A003
        return

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/portal-state":
            self.send_json(portal_state())
            return
        if parsed.path in {"/", "/index.html"}:
            self.send_file(PORTAL_DIR / "index.html")
            return
        target = (PORTAL_DIR / parsed.path.lstrip("/")).resolve()
        if PORTAL_DIR in target.parents and target.exists() and target.is_file():
            self.send_file(target)
            return
        self.send_error(404)

    def send_json(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        body = path.read_bytes()
        content_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("localhost", PORT), PortalHandler)
    print(f"Portal lokal aktif: http://localhost:{PORT}")
    server.serve_forever()
