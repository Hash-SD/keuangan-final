from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests


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
    definitions = [
        {"key": "portal", "name": "Portal Keuangan", "role": "Portal Lokal", "port": 8090, "url": "http://localhost:8090", "kind": "http"},
        {"key": "airflow", "name": "Airflow", "role": "Orchestration", "port": 8085, "url": "http://localhost:8085", "kind": "http"},
        {"key": "superset", "name": "Superset", "role": "BI Dashboard", "port": 8089, "url": "http://localhost:8089", "kind": "http"},
        {"key": "supersetHealth", "name": "Superset Health", "role": "BI Healthcheck", "port": 8089, "url": "http://localhost:8089/health", "kind": "http"},
        {"key": "minioApi", "name": "MinIO API", "role": "Object Storage API", "port": 9000, "url": "http://localhost:9000", "kind": "http"},
        {"key": "minioConsole", "name": "MinIO Console", "role": "Object Storage Console", "port": 9001, "url": "http://localhost:9001", "kind": "http"},
        {"key": "sparkMaster", "name": "Spark Master", "role": "Compute Master UI", "port": 8080, "url": "http://localhost:8080", "kind": "http"},
        {"key": "sparkWorker", "name": "Spark Worker", "role": "Compute Worker UI", "port": 8081, "url": "http://localhost:8081", "kind": "http"},
        {"key": "trino", "name": "Trino", "role": "SQL Query Engine", "port": 8082, "url": "http://localhost:8082/v1/info", "kind": "http"},
        {"key": "postgres", "name": "PostgreSQL Metastore", "role": "Metadata Database", "port": 5432, "host": "localhost", "kind": "tcp", "action": "copy_connection"},
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
    return {"services": services}


def service_map() -> dict[str, bool]:
    return {item["key"]: item["status"] == "online" for item in service_statuses()["services"]}
