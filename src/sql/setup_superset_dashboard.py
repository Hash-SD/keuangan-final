from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR
from src.common.runtime_config import get_runtime_config


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")
DASHBOARD_TITLE = "Dashboard Piutang UKT Prodi"
DASHBOARD_SLUG = "dashboard-piutang-ukt-prodi"


def _request_with_wait(session: requests.Session, method: str, url: str, attempts: int = 30, **kwargs: Any) -> requests.Response:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return session.request(method, url, timeout=kwargs.pop("timeout", 30), **kwargs)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(3)
    raise RuntimeError(f"Superset API is not reachable after {attempts} attempts: {last_error}")


def _login() -> requests.Session:
    session = requests.Session()
    login = _request_with_wait(
        session,
        "POST",
        f"{BASE_URL}/api/v1/security/login",
        json={"username": "admin", "password": "admin", "provider": "db", "refresh": True},
        timeout=30,
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    csrf = _request_with_wait(session, "GET", f"{BASE_URL}/api/v1/security/csrf_token/", timeout=30)
    csrf.raise_for_status()
    session.headers.update({"X-CSRFToken": csrf.json()["result"]})
    return session


def _metric(label: str, aggregate: str, column: str) -> dict[str, Any]:
    return {
        "aggregate": aggregate,
        "column": {"column_name": column},
        "expressionType": "SIMPLE",
        "label": label,
        "optionName": f"metric_{label.lower().replace(' ', '_')}",
    }


def _filter(col: str, op: str, val: Any) -> dict[str, Any]:
    return {
        "clause": "WHERE",
        "comparator": val,
        "expressionType": "SIMPLE",
        "filterOptionName": f"filter_{col}_{op}".replace(" ", "_"),
        "isExtra": False,
        "isNew": False,
        "operator": op,
        "subject": col,
    }


def _query_filter(col: str, op: str, val: Any) -> dict[str, Any]:
    return {"col": col, "op": op, "val": val}


def _query_context(dataset_id: int, form_data: dict[str, Any], query: dict[str, Any]) -> str:
    return json.dumps(
        {
            "datasource": {"id": dataset_id, "type": "table"},
            "force": False,
            "queries": [query],
            "form_data": form_data,
            "result_format": "json",
            "result_type": "full",
        }
    )


def _chart_payload(dataset_id: int, name: str, viz_type: str, form_data: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    form_data = {
        "datasource": f"{dataset_id}__table",
        "viz_type": viz_type,
        "adhoc_filters": [],
        "row_limit": 10000,
        **form_data,
    }
    query = {
        "filters": [],
        "extras": {"having": "", "where": ""},
        "applied_time_extras": {},
        "annotation_layers": [],
        "row_limit": 10000,
        "series_limit": 0,
        **query,
    }
    return {
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": json.dumps(form_data),
        "query_context": _query_context(dataset_id, form_data, query),
    }


def _get_items(session: requests.Session, resource: str) -> list[dict[str, Any]]:
    response = session.get(f"{BASE_URL}/api/v1/{resource}/?page_size=500", timeout=30)
    response.raise_for_status()
    return response.json().get("result", [])


def _upsert_chart(session: requests.Session, payload: dict[str, Any]) -> int:
    charts = _get_items(session, "chart")
    existing = next((item for item in charts if item.get("slice_name") == payload["slice_name"]), None)
    if existing:
        chart_id = existing["id"]
        response = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/chart/", json=payload, timeout=60)
    response.raise_for_status()
    return response.json().get("id") or response.json().get("result", {}).get("id") or existing["id"]


def _delete_test_assets(session: requests.Session) -> None:
    for chart in _get_items(session, "chart"):
        if str(chart.get("slice_name", "")).startswith("TEST "):
            session.delete(f"{BASE_URL}/api/v1/chart/{chart['id']}", timeout=30)
    for dashboard in _get_items(session, "dashboard"):
        if str(dashboard.get("dashboard_title", "")).startswith("TEST "):
            session.delete(f"{BASE_URL}/api/v1/dashboard/{dashboard['id']}", timeout=30)


def _upsert_dashboard(session: requests.Session, chart_ids: list[int]) -> int:
    dashboards = _get_items(session, "dashboard")
    existing = next((item for item in dashboards if item.get("slug") == DASHBOARD_SLUG or item.get("dashboard_title") == DASHBOARD_TITLE), None)
    base_payload = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": DASHBOARD_SLUG,
        "published": True,
        "json_metadata": json.dumps(
            {
                "label_colors": {},
                "timed_refresh_immune_slices": [],
                "expanded_slices": {},
                "refresh_frequency": 0,
                "color_namespace": "superset",
                "color_scheme": "supersetColors",
            }
        ),
    }
    if existing:
        dashboard_id = existing["id"]
        response = session.put(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", json=base_payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/dashboard/", json=base_payload, timeout=60)
        dashboard_id = response.json().get("id") or response.json().get("result", {}).get("id")
    response.raise_for_status()

    for chart_id in chart_ids:
        attach = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json={"dashboards": [dashboard_id]}, timeout=60)
        attach.raise_for_status()

    position_json = _position_json(chart_ids)
    update = session.put(
        f"{BASE_URL}/api/v1/dashboard/{dashboard_id}",
        json={**base_payload, "position_json": json.dumps(position_json)},
        timeout=60,
    )
    update.raise_for_status()
    return dashboard_id


def _position_json(chart_ids: list[int]) -> dict[str, Any]:
    rows = [["CHART-0", "CHART-1"], ["CHART-2", "CHART-3"], ["CHART-4"], ["CHART-5"]]
    layout: dict[str, Any] = {
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"}},
        "GRID_ID": {
            "type": "GRID",
            "id": "GRID_ID",
            "children": [f"ROW-{idx}" for idx in range(len(rows))],
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        },
    }
    chart_index = 0
    for row_idx, row_children in enumerate(rows):
        layout[f"ROW-{row_idx}"] = {
            "type": "ROW",
            "id": f"ROW-{row_idx}",
            "children": row_children,
            "meta": {"background": "BACKGROUND_TRANSPARENT"},
        }
        for child in row_children:
            width = 6 if len(row_children) == 2 else 12
            height = 44 if child != "CHART-5" else 62
            layout[child] = {
                "type": "CHART",
                "id": child,
                "children": [],
                "meta": {
                    "chartId": chart_ids[chart_index],
                    "height": height,
                    "width": width,
                    "background": "BACKGROUND_TRANSPARENT",
                },
            }
            chart_index += 1
    return layout


def _chart_definitions(dataset_id: int) -> list[dict[str, Any]]:
    config = get_runtime_config()
    target_prodi = config.target_prodi
    target_tahun = config.target_tahun_akademik
    total_piutang = _metric("Total Piutang", "SUM", "nominal_piutang_rp")
    jumlah_penunggak = _metric("Jumlah Penunggak", "COUNT_DISTINCT", "nim")
    count_rows = _metric("Jumlah Baris", "COUNT", "piutang_key")

    target_prodi_filter = _filter("nama_prodi", "==", target_prodi)
    target_prodi_query_filter = _query_filter("nama_prodi", "==", target_prodi)
    target_tahun_filter = _filter("tahun_akademik", "==", target_tahun)
    target_tahun_query_filter = _query_filter("tahun_akademik", "==", target_tahun)
    target_filters = [target_prodi_filter, target_tahun_filter]
    target_query_filters = [target_prodi_query_filter, target_tahun_query_filter]
    return [
        _chart_payload(
            dataset_id,
            f"Total Piutang UKT - {target_prodi} {target_tahun}",
            "big_number_total",
            {
                "metric": total_piutang,
                "adhoc_filters": target_filters,
                "header_font_size": 0.45,
                "subheader_font_size": 0.16,
                "y_axis_format": ",d",
            },
            {"metrics": [total_piutang], "columns": [], "filters": target_query_filters, "orderby": [[total_piutang, False]]},
        ),
        _chart_payload(
            dataset_id,
            f"Jumlah Mahasiswa Penunggak - {target_prodi} {target_tahun}",
            "big_number_total",
            {
                "metric": jumlah_penunggak,
                "adhoc_filters": target_filters,
                "header_font_size": 0.45,
                "subheader_font_size": 0.16,
                "y_axis_format": ",d",
            },
            {"metrics": [jumlah_penunggak], "columns": [], "filters": target_query_filters, "orderby": [[jumlah_penunggak, False]]},
        ),
        _chart_payload(
            dataset_id,
            "Piutang UKT per Prodi",
            "echarts_timeseries_bar",
            {
                "metrics": [total_piutang],
                "x_axis": "nama_prodi",
                "orientation": "vertical",
                "show_legend": False,
                "y_axis_format": ",d",
                "sort_series_type": "sum",
            },
            {"metrics": [total_piutang], "columns": ["nama_prodi"], "orderby": [[total_piutang, False]]},
        ),
        _chart_payload(
            dataset_id,
            "Distribusi Kualitas Piutang",
            "pie",
            {
                "metric": count_rows,
                "groupby": ["kualitas"],
                "show_labels": True,
                "show_legend": True,
                "label_type": "key_percent",
            },
            {"metrics": [count_rows], "columns": ["kualitas"], "orderby": [[count_rows, False]]},
        ),
        _chart_payload(
            dataset_id,
            "Tren Piutang per Semester",
            "echarts_timeseries_line",
            {
                "metrics": [total_piutang],
                "x_axis": "semester",
                "show_legend": False,
                "y_axis_format": ",d",
            },
            {"metrics": [total_piutang], "columns": ["semester"], "orderby": [["semester", True]]},
        ),
        _chart_payload(
            dataset_id,
            "Rincian Piutang Mahasiswa",
            "table",
            {
                "all_columns": ["nama_prodi", "nim", "nama_debitur", "semester", "kualitas", "nominal_piutang_rp"],
                "order_by_cols": ["[\"nominal_piutang_rp\", false]"],
                "page_length": 25,
                "table_timestamp_format": "smart_date",
            },
            {
                "columns": ["nama_prodi", "nim", "nama_debitur", "semester", "kualitas", "nominal_piutang_rp"],
                "metrics": [],
                "orderby": [["nominal_piutang_rp", False]],
            },
        ),
    ]


def main() -> None:
    session = _login()
    _delete_test_assets(session)
    asset_path = OUTPUTS_DIR / "reports" / "superset_assets.json"
    if not asset_path.exists():
        raise FileNotFoundError("Run setup_superset_assets.py before setup_superset_dashboard.py")
    dataset_id = json.loads(asset_path.read_text(encoding="utf-8"))["dataset_id"]
    chart_ids = [_upsert_chart(session, payload) for payload in _chart_definitions(dataset_id)]
    dashboard_id = _upsert_dashboard(session, chart_ids)
    result = {
        "dashboard_id": dashboard_id,
        "dashboard_title": DASHBOARD_TITLE,
        "dashboard_url": f"{BASE_URL}/superset/dashboard/{DASHBOARD_SLUG}/",
        "chart_ids": chart_ids,
    }
    write_json(OUTPUTS_DIR / "reports" / "superset_dashboard.json", result)
    print(result)


if __name__ == "__main__":
    main()
