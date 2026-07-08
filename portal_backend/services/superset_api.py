from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .paths import OUTPUTS_DIR


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089").rstrip("/")
USERNAME = os.getenv("SUPERSET_USERNAME", "admin")
PASSWORD = os.getenv("SUPERSET_PASSWORD", "admin")
TIMEOUT_SECONDS = float(os.getenv("SUPERSET_API_TIMEOUT_SECONDS", "1.0"))

FACT_COLUMNS = [
    "item_id",
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
    login = session.post(
        f"{BASE_URL}/api/v1/security/login",
        json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
        timeout=TIMEOUT_SECONDS,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    csrf = session.get(f"{BASE_URL}/api/v1/security/csrf_token/", timeout=TIMEOUT_SECONDS)
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
        response = session.post(f"{BASE_URL}/api/v1/chart/data", json=_chart_data_payload(int(dataset_id), filters=filters, limit=limit), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        result = response.json().get("result") or []
        data = result[0].get("data") if result and isinstance(result[0], dict) else []
        frame = pd.DataFrame(data or [])
        return frame, {"status": "ready", "source_kind": "superset_api", "source_dataset": "fact_anggaran", "superset_reference": reference}
    except Exception as exc:
        return None, {"status": "unreachable", "message": str(exc), "superset_reference": reference}
