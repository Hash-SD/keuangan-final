from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .paths import OUTPUTS_DIR


USERNAME = os.getenv("SUPERSET_USERNAME", "admin")
PASSWORD = os.getenv("SUPERSET_PASSWORD", "admin")


def _base_url() -> str:
    explicit = os.getenv("SUPERSET_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    host = os.getenv("SUPERSET_HOST", "localhost")
    port = os.getenv("SUPERSET_PORT", "8089")
    return f"http://{host}:{port}".rstrip("/")


def _timeout_seconds() -> float:
    return float(os.getenv("SUPERSET_API_TIMEOUT_SECONDS", "5.0"))

FACT_COLUMNS = [
    "item_id",
    "dataset_session_id",
    "run_id",
    "tahun",
    "periode",
    "prodi",
    "fakultas",
    "kegiatan",
    "akun",
    "iku",
    "jumlah",
    "jumlah_weighted_iku",
    "mapping_status",
    "data_quality_flag",
    "uraian_detail",
]


def read_superset_reference() -> dict[str, Any]:
    payload = _read_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json") or _read_json(OUTPUTS_DIR / "reports" / "superset_excel_assets.json") or {}
    return {
        "status": payload.get("status") or "not_available",
        "superset_api_status": payload.get("superset_api_status"),
        "dataset_id": payload.get("dataset_id"),
        "dashboard_id": payload.get("dashboard_id"),
        "dashboard_url": payload.get("dashboard_url"),
        "dashboard_canonical_url": payload.get("dashboard_canonical_url"),
        "chart_ids": payload.get("chart_ids") or [],
        "table_name": payload.get("table_name") or "fact_anggaran",
    }


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _login() -> requests.Session:
    session = requests.Session()
    base_url = _base_url()
    timeout = _timeout_seconds()
    login = session.post(
        f"{base_url}/api/v1/security/login",
        json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
        timeout=timeout,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    csrf = session.get(f"{base_url}/api/v1/security/csrf_token/", timeout=timeout)
    csrf.raise_for_status()
    session.headers.update({"X-CSRFToken": csrf.json()["result"]})
    return session


def _chart_data_payload(dataset_id: int, filters: dict[str, list[str]] | None = None, limit: int = 10000) -> dict[str, Any]:
    adhoc_filters = []
    for column, values in (filters or {}).items():
        if not values:
            continue
        subject = {
            "tahun_anggaran": "tahun",
            "semester": "periode",
            "nama_prodi": "prodi",
            "nama_fakultas": "fakultas",
            "kualitas": "data_quality_flag",
        }.get(column, column)
        adhoc_filters.append(
            {
                "clause": "WHERE",
                "comparator": values,
                "expressionType": "SIMPLE",
                "operator": "IN",
                "subject": subject,
            }
        )
    query = {
        "columns": FACT_COLUMNS,
        "metrics": [],
        "filters": [],
        "extras": {"having": "", "where": ""},
        "applied_time_extras": {},
        "annotation_layers": [],
        "row_limit": limit,
        "series_limit": 0,
    }
    form_data = {
        "datasource": f"{dataset_id}__table",
        "viz_type": "table",
        "all_columns": FACT_COLUMNS,
        "adhoc_filters": adhoc_filters,
        "row_limit": limit,
        "time_range": "No filter",
    }
    return {
        "datasource": {"id": dataset_id, "type": "table"},
        "force": False,
        "queries": [query],
        "form_data": form_data,
        "result_format": "json",
        "result_type": "full",
    }


def fetch_superset_fact_rows(filters: dict[str, list[str]] | None = None, limit: int = 10000) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    reference = read_superset_reference()
    dataset_id = reference.get("dataset_id")
    if not dataset_id:
        return None, {"status": "not_available", "message": "Superset dataset_id belum tersedia.", "superset_reference": reference}
    try:
        session = _login()
        response = session.post(f"{_base_url()}/api/v1/chart/data", json=_chart_data_payload(int(dataset_id), filters=filters, limit=limit), timeout=_timeout_seconds())
        response.raise_for_status()
        result = response.json().get("result") or []
        data = result[0].get("data") if result and isinstance(result[0], dict) else []
        frame = pd.DataFrame(data or [])
        return frame, {"status": "ready", "source_kind": "superset_api", "source_dataset": "fact_anggaran", "superset_reference": reference}
    except Exception as exc:
        return None, {"status": "unreachable", "message": str(exc), "superset_reference": reference}


def record_dashboard_verification(dataset_session_id: str, pipeline_run_id: str) -> dict[str, Any]:
    frame, evidence = fetch_superset_fact_rows({"dataset_session_id": [dataset_session_id], "run_id": [pipeline_run_id]})
    if frame is None or frame.empty:
        return {"status": "not_available", "message": "Superset belum membaca data untuk dataset/run aktif.", "evidence": evidence}
    manifest_path = OUTPUTS_DIR / "reports" / "pipeline_runs" / f"{pipeline_run_id}.json"
    manifest = _read_json(manifest_path) or {}
    if manifest.get("dataset_session_id") != dataset_session_id:
        return {"status": "invalid", "message": "Manifest tidak cocok dengan dataset yang diverifikasi."}
    if manifest.get("pipeline_run_id") != pipeline_run_id:
        return {"status": "invalid", "message": "Manifest tidak cocok dengan pipeline run yang diverifikasi."}
    row_count = int(len(frame))
    weighted_total = float(pd.to_numeric(frame.get("jumlah_weighted_iku"), errors="coerce").fillna(0).sum())
    expected_rows = manifest.get("postgres_row_count") or manifest.get("fact_anggaran_rows")
    expected_total = manifest.get("postgres_weighted_total")
    if expected_rows is None or row_count != int(expected_rows):
        return {"status": "invalid", "message": "Jumlah baris Superset tidak sama dengan Gold tervalidasi."}
    if expected_total is not None and abs(weighted_total - float(expected_total)) > 0.01:
        return {"status": "invalid", "message": "Total Superset tidak sama dengan Gold tervalidasi."}
    verified_at = datetime.now(timezone.utc).isoformat()
    manifest.update({"dashboard_verified_at": verified_at, "superset_verified_row_count": row_count, "superset_verified_weighted_total": weighted_total})
    temporary = manifest_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(manifest_path)
    return {"status": "validated", "dashboard_verified_at": verified_at, "row_count": row_count, "weighted_total": weighted_total}
