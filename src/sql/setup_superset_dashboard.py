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
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR
from src.common.runtime_config import get_runtime_config
from src.common.runtime_paths import active_period_metadata


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")
PUBLIC_BASE_URL = os.getenv("SUPERSET_PUBLIC_URL", "http://localhost:8089")
DASHBOARD_TITLE = "Dashboard Piutang UKT Multi Tahun Prodi"
DASHBOARD_SLUG = "dashboard-piutang-ukt-prodi"
MANAGED_STATIC_CHART_NAMES = {
    "Total Piutang UKT",
    "Jumlah Mahasiswa Penunggak",
    "Total Piutang UKT Multi Tahun",
    "Jumlah Mahasiswa Penunggak Multi Tahun",
    "Piutang UKT per Tahun Akademik",
    "Tren Piutang per Periode",
    "Piutang UKT per Prodi",
    "Distribusi Kualitas Piutang",
    "Tren Piutang per Semester",
    "Rincian Piutang Mahasiswa Multi Tahun",
    "Rincian Piutang Mahasiswa",
}
MANAGED_CONTEXTUAL_CHART_PREFIXES = (
    "Total Piutang UKT - ",
    "Jumlah Mahasiswa Penunggak - ",
)


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


def _delete_resource(session: requests.Session, resource: str, item_id: int) -> None:
    response = session.delete(f"{BASE_URL}/api/v1/{resource}/{item_id}", timeout=30)
    if response.status_code != 404:
        response.raise_for_status()


def _is_managed_chart_name(name: str, active_names: set[str]) -> bool:
    return (
        name in active_names
        or name in MANAGED_STATIC_CHART_NAMES
        or any(name.startswith(prefix) for prefix in MANAGED_CONTEXTUAL_CHART_PREFIXES)
    )


def _deduplicate_charts_by_name(session: requests.Session, charts: list[dict[str, Any]], chart_name: str) -> dict[str, Any] | None:
    matches = [item for item in charts if item.get("slice_name") == chart_name]
    if not matches:
        return None
    matches.sort(key=lambda item: int(item["id"]))
    keep = matches[0]
    for duplicate in matches[1:]:
        _delete_resource(session, "chart", duplicate["id"])
    return keep


def _upsert_chart(session: requests.Session, payload: dict[str, Any]) -> int:
    charts = _get_items(session, "chart")
    existing = _deduplicate_charts_by_name(session, charts, payload["slice_name"])
    chart_id = None
    if existing:
        chart_id = existing["id"]
        response = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/chart/", json=payload, timeout=60)
    response.raise_for_status()
    chart_id = response.json().get("id") or response.json().get("result", {}).get("id") or chart_id
    if chart_id is None:
        raise RuntimeError(f"Superset did not return an id for chart {payload['slice_name']!r}")
    return chart_id


def _delete_stale_managed_charts(session: requests.Session, active_chart_ids: list[int], active_names: set[str]) -> None:
    active_ids = set(active_chart_ids)
    for chart in _get_items(session, "chart"):
        chart_id = chart.get("id")
        chart_name = str(chart.get("slice_name", ""))
        if chart_id not in active_ids and _is_managed_chart_name(chart_name, active_names):
            _delete_resource(session, "chart", chart_id)


def _delete_test_assets(session: requests.Session) -> None:
    for chart in _get_items(session, "chart"):
        if str(chart.get("slice_name", "")).startswith("TEST "):
            session.delete(f"{BASE_URL}/api/v1/chart/{chart['id']}", timeout=30)
    for dashboard in _get_items(session, "dashboard"):
        if str(dashboard.get("dashboard_title", "")).startswith("TEST "):
            session.delete(f"{BASE_URL}/api/v1/dashboard/{dashboard['id']}", timeout=30)


def _upsert_dashboard(session: requests.Session, chart_ids: list[int]) -> int:
    dashboards = _get_items(session, "dashboard")
    matches = [item for item in dashboards if item.get("slug") == DASHBOARD_SLUG or item.get("dashboard_title") == DASHBOARD_TITLE]
    matches.sort(key=lambda item: int(item["id"]))
    existing = matches[0] if matches else None
    for duplicate in matches[1:]:
        _delete_resource(session, "dashboard", duplicate["id"])
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
                "native_filter_configuration": _native_filter_configuration(
                    dataset_id=_dashboard_dataset_id(chart_ids),
                    defaults=_runtime_filter_defaults(),
                ),
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


def _dashboard_dataset_id(chart_ids: list[int]) -> int | None:
    asset_path = OUTPUTS_DIR / "reports" / "superset_assets.json"
    if not chart_ids or not asset_path.exists():
        return None
    return json.loads(asset_path.read_text(encoding="utf-8")).get("dataset_id")


def _native_filter_configuration(dataset_id: int | None, defaults: dict[str, list[Any]] | None = None) -> list[dict[str, Any]]:
    defaults = defaults or {}

    def default_data_mask(column: str) -> dict[str, Any]:
        values = defaults.get(column) or []
        if not values:
            return {"extraFormData": {}, "filterState": {"value": None}}
        return {
            "extraFormData": {
                "adhoc_filters": [
                    {
                        "clause": "WHERE",
                        "comparator": values,
                        "expressionType": "SIMPLE",
                        "operator": "IN",
                        "subject": column,
                    }
                ]
            },
            "filterState": {"value": values},
        }

    def native_filter(filter_id: str, name: str, column: str) -> dict[str, Any]:
        return {
            "id": filter_id,
            "name": name,
            "filterType": "filter_select",
            "targets": [{"datasetId": dataset_id, "column": {"name": column}}],
            "defaultDataMask": default_data_mask(column),
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "type": "NATIVE_FILTER",
            "description": "",
            "controlValues": {"enableEmptyFilter": True, "multiSelect": True, "searchAllOptions": True},
        }

    return [
        native_filter("native_filter_tahun_akademik", "Tahun Akademik", "tahun_akademik"),
        native_filter("native_filter_tahun_anggaran", "Tahun Anggaran", "tahun_anggaran"),
        native_filter("native_filter_semester", "Semester", "semester"),
        native_filter("native_filter_prodi", "Program Studi", "nama_prodi"),
        native_filter("native_filter_kualitas", "Kualitas Piutang", "kualitas"),
    ]


def _available_filter_values() -> dict[str, set[str]]:
    path = GENERATED_DIR / "gold" / "vw_dashboard_piutang_ukt.csv"
    values = {
        "tahun_akademik": set(),
        "tahun_anggaran": set(),
        "semester": set(),
        "nama_prodi": set(),
        "kualitas": set(),
    }
    if not path.exists():
        return values
    try:
        import pandas as pd

        frame = pd.read_csv(path, dtype="string")
    except Exception:
        return values
    for column in values:
        if column in frame.columns:
            values[column] = {str(item) for item in frame[column].dropna().unique() if str(item).strip()}
    return values


def _runtime_filter_defaults(available_values: dict[str, set[str]] | None = None) -> dict[str, list[Any]]:
    config = get_runtime_config()
    period = active_period_metadata()
    target_prodi = period.get("target_prodi") or config.target_prodi
    target_tahun_akademik = period.get("target_tahun_akademik") or config.target_tahun_akademik
    target_tahun_anggaran = period.get("target_tahun_anggaran") or config.target_tahun_anggaran
    available_values = available_values if available_values is not None else _available_filter_values()
    defaults = {"nama_prodi": [target_prodi]}
    if target_tahun_akademik in available_values.get("tahun_akademik", set()):
        defaults["tahun_akademik"] = [target_tahun_akademik]
    if target_tahun_anggaran in available_values.get("tahun_anggaran", set()):
        defaults["tahun_anggaran"] = [int(target_tahun_anggaran) if target_tahun_anggaran.isdigit() else target_tahun_anggaran]
    return defaults


def _chart_static_locks(chart_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    locked_columns = {"nama_prodi", "tahun_akademik", "tahun_anggaran"}
    locks = []
    for payload in chart_payloads:
        params = json.loads(payload.get("params") or "{}")
        context = json.loads(payload.get("query_context") or "{}")
        for item in params.get("adhoc_filters", []):
            if item.get("subject") in locked_columns:
                locks.append({"chart": payload["slice_name"], "location": "params.adhoc_filters", "filter": item})
        for query in context.get("queries", []):
            for item in query.get("filters", []):
                if item.get("col") in locked_columns:
                    locks.append({"chart": payload["slice_name"], "location": "query_context.filters", "filter": item})
    return locks


def _dashboard_filter_validation(
    session: requests.Session,
    dashboard_id: int,
    dataset_id: int,
    chart_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    response = session.get(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", timeout=30)
    response.raise_for_status()
    result = response.json().get("result", {})
    metadata = result.get("json_metadata") or "{}"
    if isinstance(metadata, str):
        metadata = json.loads(metadata or "{}")
    filters = metadata.get("native_filter_configuration", [])
    default_values = {
        item.get("name"): item.get("defaultDataMask", {}).get("filterState", {}).get("value")
        for item in filters
    }
    default_extra_form_data = {
        item.get("name"): item.get("defaultDataMask", {}).get("extraFormData", {})
        for item in filters
    }
    excluded_scopes = {item.get("name"): item.get("scope", {}).get("excluded", []) for item in filters}
    enable_empty_filter = {
        item.get("name"): item.get("controlValues", {}).get("enableEmptyFilter")
        for item in filters
    }
    static_locks = _chart_static_locks(chart_payloads)
    unlocked = (
        bool(filters)
        and all(value == [] for value in excluded_scopes.values())
        and all(value is True for value in enable_empty_filter.values())
        and not static_locks
    )
    return {
        "status": "validated",
        "superset_api_status": "ready",
        "dashboard_id": dashboard_id,
        "dataset_id": dataset_id,
        "filter_count": len(filters),
        "filter_columns": [
            item.get("targets", [{}])[0].get("column", {}).get("name")
            for item in filters
        ],
        "filters_created": [item.get("name") for item in filters],
        "default_values": default_values,
        "default_filter": default_values,
        "default_extra_form_data": default_extra_form_data,
        "excluded_scopes": excluded_scopes,
        "enable_empty_filter": enable_empty_filter,
        "has_static_lock": bool(static_locks),
        "static_locks": static_locks,
        "charts_follow_native_filter": not static_locks and all(item.get("scope", {}).get("excluded", []) == [] for item in filters),
        "unlocked": unlocked,
        "message": "Native filters memiliki default awal yang bisa dihapus dan tidak ada static chart lock." if unlocked else "Native filter atau chart lock masih perlu diperiksa.",
    }


def _position_json(chart_ids: list[int]) -> dict[str, Any]:
    rows: list[list[str]] = []
    for idx in range(0, len(chart_ids), 2):
        rows.append([f"CHART-{child}" for child in range(idx, min(idx + 2, len(chart_ids)))])
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
            height = 44 if chart_index < len(chart_ids) - 1 else 62
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
    total_piutang = _metric("Total Piutang", "SUM", "nominal_piutang_rp")
    jumlah_penunggak = _metric("Jumlah Penunggak", "COUNT_DISTINCT", "nim")
    count_rows = _metric("Jumlah Baris", "COUNT", "piutang_key")

    return [
        _chart_payload(
            dataset_id,
            "Total Piutang UKT",
            "big_number_total",
            {
                "metric": total_piutang,
                "header_font_size": 0.45,
                "subheader_font_size": 0.16,
                "y_axis_format": ",d",
            },
            {"metrics": [total_piutang], "columns": [], "orderby": [[total_piutang, False]]},
        ),
        _chart_payload(
            dataset_id,
            "Jumlah Mahasiswa Penunggak",
            "big_number_total",
            {
                "metric": jumlah_penunggak,
                "header_font_size": 0.45,
                "subheader_font_size": 0.16,
                "y_axis_format": ",d",
            },
            {"metrics": [jumlah_penunggak], "columns": [], "orderby": [[jumlah_penunggak, False]]},
        ),
        _chart_payload(
            dataset_id,
            "Tren Piutang per Semester",
            "echarts_timeseries_line",
            {
                "metrics": [total_piutang],
                "x_axis": "semester",
                "groupby": ["tahun_akademik"],
                "show_legend": True,
                "y_axis_format": ",d",
            },
            {"metrics": [total_piutang], "columns": ["semester", "tahun_akademik"], "orderby": [["tahun_akademik", True], ["semester", True]]},
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
            "Rincian Piutang Mahasiswa",
            "table",
            {
                "all_columns": [
                    "dataset_session_id",
                    "tahun_akademik",
                    "tahun_anggaran",
                    "semester",
                    "periode_key",
                    "nama_prodi",
                    "nim",
                    "nama_debitur",
                    "kualitas",
                    "nominal_piutang_rp",
                ],
                "order_by_cols": ["[\"nominal_piutang_rp\", false]"],
                "page_length": 25,
                "table_timestamp_format": "smart_date",
            },
            {
                "columns": [
                    "dataset_session_id",
                    "tahun_akademik",
                    "tahun_anggaran",
                    "semester",
                    "periode_key",
                    "nama_prodi",
                    "nim",
                    "nama_debitur",
                    "kualitas",
                    "nominal_piutang_rp",
                ],
                "metrics": [],
                "orderby": [["nominal_piutang_rp", False]],
            },
        ),
    ]


def main() -> None:
    asset_path = OUTPUTS_DIR / "reports" / "superset_assets.json"
    try:
        session = _login()
        _delete_test_assets(session)
        if not asset_path.exists():
            raise FileNotFoundError("Run setup_superset_assets.py before setup_superset_dashboard.py")
        dataset_id = json.loads(asset_path.read_text(encoding="utf-8"))["dataset_id"]
        chart_definitions = _chart_definitions(dataset_id)
        active_names = {payload["slice_name"] for payload in chart_definitions}
        chart_ids = [_upsert_chart(session, payload) for payload in chart_definitions]
        _delete_stale_managed_charts(session, chart_ids, active_names)
        dashboard_id = _upsert_dashboard(session, chart_ids)
        filter_validation = _dashboard_filter_validation(session, dashboard_id, dataset_id, chart_definitions)
    except requests.RequestException as exc:
        result = {
            "status": "unreachable",
            "superset_api_status": "unreachable",
            "dashboard_id": None,
            "dataset_id": None,
            "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{DASHBOARD_SLUG}/",
            "message": f"Superset unreachable: {exc}",
        }
        write_json(OUTPUTS_DIR / "reports" / "superset_dashboard_status.json", result)
        write_json(OUTPUTS_DIR / "reports" / "superset_filters_validation.json", result)
        print(result)
        return
    result = {
        "status": "validated",
        "superset_api_status": "ready",
        "dashboard_id": dashboard_id,
        "dataset_id": dataset_id,
        "dashboard_title": DASHBOARD_TITLE,
        "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{DASHBOARD_SLUG}/",
        "chart_ids": chart_ids,
        "chart_count": len(chart_ids),
        "native_filter_columns": ["tahun_akademik", "tahun_anggaran", "semester", "nama_prodi", "kualitas"],
        "default_filter": filter_validation["default_filter"],
        "has_static_lock": filter_validation["has_static_lock"],
        "charts_follow_native_filter": filter_validation["charts_follow_native_filter"],
        "native_filters_unlocked": filter_validation["unlocked"],
        "dashboard_context": "multi_year",
    }
    write_json(OUTPUTS_DIR / "reports" / "superset_dashboard.json", result)
    write_json(OUTPUTS_DIR / "reports" / "superset_dashboard_status.json", result)
    write_json(OUTPUTS_DIR / "reports" / "superset_filters_validation.json", filter_validation)
    print(result)


if __name__ == "__main__":
    main()
