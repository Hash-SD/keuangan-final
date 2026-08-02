from __future__ import annotations

import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from src.status.system_truth_status import build_system_truth_status


def tcp_online(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def http_online(url: str, timeout: float = 0.25) -> bool:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except requests.RequestException:
        return False


def service_statuses() -> dict[str, list[dict[str, Any]]]:
    truth = build_system_truth_status(write_outputs=True)
    truth_services = truth.get("services", {})
    definitions = [
        {"key": "portal", "name": "Portal Keuangan", "role": "Portal Lokal", "port": 8090, "url": f"http://{os.getenv('PORTAL_HOST', 'localhost')}:{os.getenv('PORTAL_PORT', '8090')}", "kind": "http"},
        {"key": "portalBackend", "name": "Portal Backend API", "role": "Local API", "port": 8091, "url": f"http://{os.getenv('PORTAL_BACKEND_HOST', 'localhost')}:{os.getenv('PORTAL_BACKEND_PORT', '8091')}/api/health", "kind": "http"},
        {"key": "airflow", "name": "Airflow", "role": "Orchestration", "port": 8085, "url": f"http://{os.getenv('AIRFLOW_HOST', 'localhost')}:{os.getenv('AIRFLOW_PORT', '8085')}", "kind": "http"},
        {"key": "superset", "name": "Superset", "role": "BI Dashboard", "port": 8089, "url": f"http://{os.getenv('SUPERSET_HOST', 'localhost')}:{os.getenv('SUPERSET_PORT', '8089')}", "kind": "http"},
        {"key": "supersetHealth", "name": "Superset Health", "role": "BI Healthcheck", "port": 8089, "url": f"http://{os.getenv('SUPERSET_HOST', 'localhost')}:{os.getenv('SUPERSET_PORT', '8089')}/health", "kind": "http"},
        {"key": "minioApi", "name": "MinIO API", "role": "Object Storage API Health", "port": 9000, "url": f"http://{os.getenv('MINIO_HOST', 'localhost')}:{os.getenv('MINIO_API_PORT', '9000')}/minio/health/live", "kind": "http"},
        {"key": "minioConsole", "name": "MinIO Console", "role": "Object Storage Console", "port": 9001, "url": f"http://{os.getenv('MINIO_HOST', 'localhost')}:{os.getenv('MINIO_CONSOLE_PORT', '9001')}", "kind": "http"},
        {"key": "sparkMaster", "name": "Spark Master", "role": "Compute Master UI", "port": 8080, "url": f"http://{os.getenv('SPARK_MASTER_HOST', 'localhost')}:{os.getenv('SPARK_MASTER_UI_PORT', '8080')}", "kind": "http"},
        {"key": "sparkRpc", "name": "Spark Master RPC", "role": "Compute Master TCP", "port": 7077, "host": os.getenv("SPARK_MASTER_HOST", "localhost"), "kind": "tcp", "action": "copy_connection"},
        {"key": "sparkWorker", "name": "Spark Worker", "role": "Compute Worker UI", "port": 8081, "url": f"http://{os.getenv('SPARK_WORKER_HOST', 'localhost')}:{os.getenv('SPARK_WORKER_UI_PORT', '8081')}", "kind": "http"},
        {"key": "trino", "name": "Trino", "role": "SQL Query Engine", "port": 8082, "url": f"http://{os.getenv('TRINO_HOST', 'localhost')}:{os.getenv('TRINO_PORT', '8082')}/v1/info", "kind": "http"},
        {"key": "postgres", "name": "PostgreSQL Metastore", "role": "Metadata Database", "port": 5432, "host": os.getenv("POSTGRES_HOST", "localhost"), "kind": "tcp", "action": "copy_connection"},
    ]
    def check(service: dict[str, Any]) -> dict[str, Any]:
        if service["kind"] == "tcp":
            online = tcp_online(service["host"], service["port"])
        else:
            online = http_online(service["url"])
        return {**service, "status": "online" if online else "offline"}

    services_by_key: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(definitions)) as executor:
        future_map = {executor.submit(check, service): service["key"] for service in definitions}
        for future in as_completed(future_map):
            key = future_map[future]
            try:
                services_by_key[key] = future.result()
            except Exception:
                original = next(service for service in definitions if service["key"] == key)
                services_by_key[key] = {**original, "status": "unknown"}

    services = [services_by_key[service["key"]] for service in definitions]
    for service in services:
        truth_item = truth_services.get(service["key"])
        if truth_item:
            service["truth_status"] = truth_item.get("status")
            service["status"] = "online" if truth_item.get("status") == "ready" else "offline"
            service["message"] = truth_item.get("message")
    if "docker" in truth_services:
        d_status = truth_services["docker"].get("status")
        is_online = d_status in ["ready", "running", "empty"] or any(s.get("status") == "online" for s in services if s.get("key") in ["postgres", "airflow", "minioApi"])
        services.append({
            "key": "docker",
            "name": "Docker Engine",
            "role": "Container Runtime",
            "status": "online" if is_online else "offline",
            "truth_status": "ready" if is_online else d_status,
            "message": "Docker Engine aktif dan beroperasi normal."
        })
    return {"services": services}


def service_map() -> dict[str, bool]:
    return {item["key"]: item["status"] == "online" for item in service_statuses()["services"]}
