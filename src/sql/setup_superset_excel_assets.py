from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import OUTPUTS_DIR


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")
PUBLIC_BASE_URL = os.getenv("SUPERSET_PUBLIC_URL", "http://localhost:8089")
DATABASE_NAME = "Trino PostgreSQL Gold Keuangan"
TABLE_NAME = "fact_anggaran"
DASHBOARD_TITLE = "SILARAS SD - Dashboard Anggaran IKU"
DASHBOARD_SLUG = "dashboard-anggaran-iku-prodi"


def _request_with_wait(session: requests.Session, method: str, url: str, attempts: int = 30, **kwargs) -> requests.Response:
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
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    csrf = _request_with_wait(session, "GET", f"{BASE_URL}/api/v1/security/csrf_token/")
    csrf.raise_for_status()
    session.headers.update({"X-CSRFToken": csrf.json()["result"]})
    return session


def _get_items(session: requests.Session, resource: str) -> list[dict]:
    response = session.get(f"{BASE_URL}/api/v1/{resource}/?page_size=500", timeout=30)
    response.raise_for_status()
    return response.json().get("result", [])


def _database_id(session: requests.Session) -> int:
    payload = {
        "database_name": DATABASE_NAME,
        "sqlalchemy_uri": "trino://trino@trino:8080/postgres/gold",
        "expose_in_sqllab": True,
        "allow_ctas": True,
        "allow_cvas": True,
        "allow_dml": False,
    }
    response = session.post(f"{BASE_URL}/api/v1/database/", json=payload, timeout=60)
    if response.status_code not in {200, 201, 422}:
        response.raise_for_status()
    for item in _get_items(session, "database"):
        if item.get("database_name") == DATABASE_NAME:
            return int(item["id"])
    result = response.json().get("result", {})
    database_id = response.json().get("id") or result.get("id")
    if database_id is None:
        raise RuntimeError(f"Superset database {DATABASE_NAME!r} was not created or found")
    return int(database_id)


def _dataset_id(session: requests.Session, database_id: int) -> int:
    payload = {"database": database_id, "catalog": "postgres", "schema": "gold", "table_name": TABLE_NAME}
    response = session.post(f"{BASE_URL}/api/v1/dataset/", json=payload, timeout=60)
    if response.status_code not in {200, 201, 422}:
        response.raise_for_status()
    datasets = session.get(f"{BASE_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:{TABLE_NAME})))", timeout=30)
    datasets.raise_for_status()
    result = datasets.json().get("result", [])
    if result:
        dataset_id = int(result[0]["id"])
        update = session.put(f"{BASE_URL}/api/v1/dataset/{dataset_id}", json={"database_id": database_id, "catalog": "postgres", "schema": "gold", "table_name": TABLE_NAME}, timeout=60)
        update.raise_for_status()
    else:
        raw_dataset_id = response.json().get("id") or response.json().get("result", {}).get("id")
        if raw_dataset_id is None:
            raise RuntimeError(f"Superset dataset {TABLE_NAME!r} was not created or found")
        dataset_id = int(raw_dataset_id)
    refresh = session.put(f"{BASE_URL}/api/v1/dataset/{dataset_id}/refresh", timeout=60)
    refresh.raise_for_status()
    return dataset_id


def _metric(label: str, aggregate: str, column: str) -> dict:
    return {
        "aggregate": aggregate,
        "column": {"column_name": column},
        "expressionType": "SIMPLE",
        "label": label,
        "optionName": f"metric_{label.lower().replace(' ', '_')}",
    }


def _chart_payload(dataset_id: int, name: str, viz_type: str, form_data: dict, query: dict) -> dict:
    form_data = {"datasource": f"{dataset_id}__table", "viz_type": viz_type, "row_limit": 10000, "adhoc_filters": [], **form_data}
    query = {"filters": [], "extras": {"having": "", "where": ""}, "applied_time_extras": {}, "annotation_layers": [], "row_limit": 10000, "series_limit": 0, **query}
    return {
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": __import__("json").dumps(form_data),
        "query_context": __import__("json").dumps({"datasource": {"id": dataset_id, "type": "table"}, "force": False, "queries": [query], "form_data": form_data, "result_format": "json", "result_type": "full"}),
    }


def _upsert_chart(session: requests.Session, payload: dict) -> int:
    matches = [item for item in _get_items(session, "chart") if item.get("slice_name") == payload["slice_name"]]
    if matches:
        chart_id = int(sorted(matches, key=lambda item: int(item["id"]))[0]["id"])
        response = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/chart/", json=payload, timeout=60)
        chart_id = None
    response.raise_for_status()
    return int(response.json().get("id") or response.json().get("result", {}).get("id") or chart_id)


def _position_json(chart_ids: list[int]) -> dict:
    layout = {
        "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"], "meta": {"background": "BACKGROUND_TRANSPARENT"}},
        "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": [], "meta": {"background": "BACKGROUND_TRANSPARENT"}},
    }
    for idx, chart_id in enumerate(chart_ids):
        row_id = f"ROW-{idx}"
        chart_node = f"CHART-{idx}"
        layout["GRID_ID"]["children"].append(row_id)
        layout[row_id] = {"type": "ROW", "id": row_id, "children": [chart_node], "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        layout[chart_node] = {"type": "CHART", "id": chart_node, "children": [], "meta": {"chartId": chart_id, "height": 48, "width": 12}}
    return layout


def _native_filters(dataset_id: int) -> list[dict]:
    def nf(filter_id: str, label: str, column: str) -> dict:
        return {
            "id": filter_id,
            "name": label,
            "filterType": "filter_select",
            "targets": [{"datasetId": dataset_id, "column": {"name": column}}],
            "defaultDataMask": {"extraFormData": {}, "filterState": {"value": None}},
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "type": "NATIVE_FILTER",
            "controlValues": {"enableEmptyFilter": True, "multiSelect": True, "searchAllOptions": True},
        }
    return [
        nf("filter_tahun", "Tahun", "tahun"),
        nf("filter_prodi", "Prodi", "prodi"),
        nf("filter_iku", "IKU", "kode_iku"),
        nf("filter_kegiatan", "Kegiatan", "kegiatan"),
        nf("filter_akun", "Akun", "akun"),
        nf("filter_quality", "Data Quality", "data_quality_flag"),
    ]


def _upsert_dashboard(session: requests.Session, dataset_id: int, chart_ids: list[int]) -> int:
    import json

    payload = {
        "dashboard_title": DASHBOARD_TITLE,
        "slug": DASHBOARD_SLUG,
        "published": True,
        "json_metadata": json.dumps({"native_filter_configuration": _native_filters(dataset_id), "color_namespace": "superset", "color_scheme": "supersetColors"}),
        "position_json": json.dumps(_position_json(chart_ids)),
    }
    matches = [item for item in _get_items(session, "dashboard") if item.get("slug") == DASHBOARD_SLUG or item.get("dashboard_title") == DASHBOARD_TITLE]
    if matches:
        dashboard_id = int(sorted(matches, key=lambda item: int(item["id"]))[0]["id"])
        response = session.put(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/dashboard/", json=payload, timeout=60)
        dashboard_id = None
    response.raise_for_status()
    dashboard_id = int(response.json().get("id") or response.json().get("result", {}).get("id") or dashboard_id)
    for chart_id in chart_ids:
        attach = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json={"dashboards": [dashboard_id]}, timeout=60)
        attach.raise_for_status()
    return dashboard_id


def main() -> None:
    try:
        session = _login()
        database_id = _database_id(session)
        dataset_id = _dataset_id(session, database_id)
        total_anggaran = _metric("Total Anggaran", "SUM", "jumlah_weighted_iku")
        total_weighted = _metric("Total Weighted IKU", "SUM", "jumlah_weighted_iku")
        count_items = _metric("Jumlah Item", "COUNT_DISTINCT", "item_id")
        count_iku = _metric("Jumlah IKU", "COUNT_DISTINCT", "kode_iku")
        count_kegiatan = _metric("Jumlah Kegiatan", "COUNT_DISTINCT", "kegiatan")
        mapped_iku_filter = [{"col": "kode_iku", "op": "IS NOT NULL", "val": None}]
        chart_payloads = [
            _chart_payload(dataset_id, "Executive KPI - Total Anggaran", "big_number_total", {"metric": total_anggaran, "y_axis_format": ",d"}, {"metrics": [total_anggaran], "columns": []}),
            _chart_payload(dataset_id, "Executive KPI - Total Weighted IKU", "big_number_total", {"metric": total_weighted, "y_axis_format": ",d"}, {"metrics": [total_weighted], "columns": []}),
            _chart_payload(dataset_id, "Executive KPI - Jumlah Item", "big_number_total", {"metric": count_items, "y_axis_format": ",d"}, {"metrics": [count_items], "columns": []}),
            _chart_payload(dataset_id, "Executive KPI - Jumlah IKU", "big_number_total", {"metric": count_iku, "y_axis_format": ",d"}, {"metrics": [count_iku], "columns": [], "filters": mapped_iku_filter}),
            _chart_payload(dataset_id, "Executive KPI - Jumlah Kegiatan", "big_number_total", {"metric": count_kegiatan, "y_axis_format": ",d"}, {"metrics": [count_kegiatan], "columns": []}),
            _chart_payload(dataset_id, "Anggaran per IKU", "echarts_timeseries_bar", {"metrics": [total_weighted], "x_axis": "kode_iku", "orientation": "vertical", "y_axis_format": ",d"}, {"metrics": [total_weighted], "columns": ["kode_iku"], "orderby": [[total_weighted, False]], "filters": mapped_iku_filter}),
            _chart_payload(dataset_id, "Cluster Kegiatan", "treemap_v2", {"metric": total_anggaran, "groupby": ["kode_iku", "kegiatan"], "label_type": "key_value"}, {"metrics": [total_anggaran], "columns": ["kode_iku", "kegiatan"], "filters": mapped_iku_filter}),
            _chart_payload(dataset_id, "Komposisi Akun", "echarts_timeseries_bar", {"metrics": [total_anggaran], "x_axis": "akun", "orientation": "horizontal", "y_axis_format": ",d", "row_limit": 25}, {"metrics": [total_anggaran], "columns": ["akun"], "orderby": [[total_anggaran, False]], "row_limit": 25}),
            _chart_payload(dataset_id, "Anggaran per Akun", "echarts_timeseries_bar", {"metrics": [total_anggaran], "x_axis": "akun", "orientation": "vertical", "y_axis_format": ",d"}, {"metrics": [total_anggaran], "columns": ["akun"], "orderby": [[total_anggaran, False]]}),
            _chart_payload(dataset_id, "Mapping Quality", "pie", {"metric": count_items, "groupby": ["mapping_status"], "label_type": "key_percent"}, {"metrics": [count_items], "columns": ["mapping_status"]}),
            _chart_payload(dataset_id, "Detail Item Biaya", "table", {"all_columns": ["tahun", "periode", "prodi", "iku", "kegiatan", "akun", "uraian_detail", "qty", "harga_satuan", "jumlah", "mapping_status", "data_quality_flag", "source_file", "source_sheet", "source_row"], "page_length": 25}, {"columns": ["tahun", "periode", "prodi", "iku", "kegiatan", "akun", "qty", "harga_satuan", "jumlah", "mapping_status", "data_quality_flag", "source_file", "source_sheet", "source_row"], "metrics": []}),
            _chart_payload(dataset_id, "Validasi Rekap", "table", {"all_columns": ["tahun", "periode", "source_file", "source_sheet", "jumlah", "data_quality_flag"], "page_length": 25}, {"columns": ["tahun", "periode", "source_file", "source_sheet", "jumlah", "data_quality_flag"], "metrics": []}),
        ]
        chart_ids = [_upsert_chart(session, payload) for payload in chart_payloads]
        dashboard_id = _upsert_dashboard(session, dataset_id, chart_ids)
        result = {
            "status": "validated",
            "superset_api_status": "ready",
            "database_id": database_id,
            "dataset_id": dataset_id,
            "table_name": TABLE_NAME,
            "dashboard_id": dashboard_id,
            "dashboard_title": DASHBOARD_TITLE,
            "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{DASHBOARD_SLUG}/",
            "chart_ids": chart_ids,
            "chart_count": len(chart_ids),
        }
    except Exception as exc:
        result = {
            "status": "unreachable",
            "superset_api_status": "unreachable",
            "table_name": TABLE_NAME,
            "dashboard_title": DASHBOARD_TITLE,
            "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{DASHBOARD_SLUG}/",
            "message": str(exc),
        }
    write_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json", result)
    write_json(OUTPUTS_DIR / "reports" / "superset_excel_assets.json", result)
    print(result)


if __name__ == "__main__":
    main()
