from __future__ import annotations

import csv
import json
import mimetypes
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = os.getenv("PORTAL_HOST", "localhost")
PORT = int(os.getenv("PORTAL_PORT", "8090"))
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
        "airflow": port_open(os.getenv("AIRFLOW_HOST", "localhost"), int(os.getenv("AIRFLOW_PORT", "8085"))),
        "superset": port_open(os.getenv("SUPERSET_HOST", "localhost"), int(os.getenv("SUPERSET_PORT", "8089"))),
        "minioApi": port_open(os.getenv("MINIO_HOST", "localhost"), int(os.getenv("MINIO_API_PORT", "9000"))),
        "minioConsole": port_open(os.getenv("MINIO_HOST", "localhost"), int(os.getenv("MINIO_CONSOLE_PORT", "9001"))),
        "sparkMaster": port_open(os.getenv("SPARK_MASTER_HOST", "localhost"), int(os.getenv("SPARK_MASTER_UI_PORT", "8080"))),
        "sparkWorker": port_open(os.getenv("SPARK_WORKER_HOST", "localhost"), int(os.getenv("SPARK_WORKER_UI_PORT", "8081"))),
        "trino": port_open(os.getenv("TRINO_HOST", "localhost"), int(os.getenv("TRINO_PORT", "8082"))),
        "postgres": port_open(os.getenv("POSTGRES_HOST", "localhost"), int(os.getenv("POSTGRES_PORT", "5432"))),
        "portalBackend": port_open(os.getenv("PORTAL_BACKEND_HOST", "localhost"), int(os.getenv("PORTAL_BACKEND_PORT", "8091"))),
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
    server = ThreadingHTTPServer((HOST, PORT), PortalHandler)
    print(f"Portal lokal aktif: http://{HOST}:{PORT}")
    server.serve_forever()
