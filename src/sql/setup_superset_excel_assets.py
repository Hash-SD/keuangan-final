from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")
PUBLIC_BASE_URL = os.getenv("SUPERSET_PUBLIC_URL", "http://localhost:8089")
DATABASE_NAME = "Trino PostgreSQL Gold Keuangan"
TABLE_NAME = "fact_anggaran"
DASHBOARD_TITLE = "SILARAS SD - Dashboard Anggaran IKU"
DASHBOARD_SLUG = "dashboard-anggaran-iku-prodi"
DASHBOARD_MODE = os.getenv("SUPERSET_DASHBOARD_MODE", "update").strip().lower()


def _dashboard_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def _dashboard_title() -> str:
    if DASHBOARD_MODE == "new":
        return f"{DASHBOARD_TITLE} {_dashboard_suffix()}"
    return DASHBOARD_TITLE


def _dashboard_slug() -> str:
    if DASHBOARD_MODE == "new":
        return f"{DASHBOARD_SLUG}-{_dashboard_suffix()}"
    return DASHBOARD_SLUG


def _chart_name(name: str) -> str:
    if DASHBOARD_MODE == "new":
        return f"{name} {_dashboard_suffix()}"
    return name


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
    for item in _get_items(session, "database"):
        if item.get("database_name") == DATABASE_NAME:
            return int(item["id"])
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
    datasets = session.get(f"{BASE_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:{TABLE_NAME})))", timeout=30)
    datasets.raise_for_status()
    result = datasets.json().get("result", [])
    if result:
        dataset_id = int(result[0]["id"])
        update = session.put(f"{BASE_URL}/api/v1/dataset/{dataset_id}", json={"database_id": database_id, "catalog": "postgres", "schema": "gold", "table_name": TABLE_NAME}, timeout=60)
        update.raise_for_status()
    else:
        payload = {"database": database_id, "catalog": "postgres", "schema": "gold", "table_name": TABLE_NAME}
        response = session.post(f"{BASE_URL}/api/v1/dataset/", json=payload, timeout=60)
        if response.status_code not in {200, 201, 422}:
            response.raise_for_status()
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
    form_data = {
        "datasource": f"{dataset_id}__table",
        "viz_type": viz_type,
        "row_limit": 10000,
        "adhoc_filters": [],
        "time_range": "No filter",
        **form_data,
    }
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


def _filter_values(column: str) -> list:
    import pandas as pd

    fact_path = GENERATED_DIR / "gold" / "fact_anggaran.parquet"
    if not fact_path.exists():
        return []
    frame = pd.read_parquet(fact_path, columns=[column])
    values = frame[column].dropna().drop_duplicates().tolist()
    return sorted(values, key=lambda value: str(value))


def _default_filter_mask(column: str, values: list) -> dict:
    if not values:
        return {"extraFormData": {}, "filterState": {}, "ownState": {}}
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
        "filterState": {"value": values, "label": "Semua"},
        "ownState": {},
    }


def _native_filters(dataset_id: int, chart_ids: list[int]) -> list[dict]:
    def nf(filter_id: str, label: str, column: str, multi_select: bool = True) -> dict:
        empty_mask = {"extraFormData": {"filters": []}, "filterState": {"value": None}, "ownState": {}}
        return {
            "id": filter_id,
            "name": label,
            "filterType": "filter_select",
            "datasetId": dataset_id,
            "groupby": column,
            "adhoc_filters": [],
            "time_range": "No filter",
            "targets": [{"datasetId": dataset_id, "column": {"name": column}}],
            "defaultDataMask": empty_mask,
            "cascadeParentIds": [],
            "scope": {"rootPath": ["ROOT_ID"], "excluded": []},
            "chartsInScope": chart_ids,
            "type": "NATIVE_FILTER",
            "controlValues": {
                "enableEmptyFilter": False,
                "multiSelect": multi_select,
                "searchAllOptions": True,
                "defaultToFirstItem": False,
                "inverseSelection": False,
            },
        }
    return [
        nf("NATIVE_FILTER-tahun", "Tahun", "tahun"),
        nf("NATIVE_FILTER-prodi", "Prodi", "prodi"),
        nf("NATIVE_FILTER-iku", "IKU", "iku"),
        nf("NATIVE_FILTER-kegiatan", "Kegiatan", "kegiatan"),
        nf("NATIVE_FILTER-akun", "Akun", "akun"),
        nf("NATIVE_FILTER-quality", "Data Quality", "data_quality_flag"),
    ]


def _upsert_dashboard(session: requests.Session, dataset_id: int, chart_ids: list[int]) -> int:
    import json

    dashboard_title = _dashboard_title()
    dashboard_slug = _dashboard_slug()
    payload = {
        "dashboard_title": dashboard_title,
        "slug": dashboard_slug,
        "published": True,
        "json_metadata": json.dumps({
            "native_filter_configuration": _native_filters(dataset_id, chart_ids),
            "color_namespace": "superset",
            "color_scheme": "supersetColors",
            "show_native_filters": True,
            "label_colors": {},
            "timed_refresh_immune_slices": [],
            "filter_scopes": {},
            "chart_configuration": {str(chart_id): {"id": chart_id, "crossFilters": {"scope": "global", "chartsInScope": chart_ids}} for chart_id in chart_ids},
        }),
        "position_json": json.dumps(_position_json(chart_ids)),
    }
    matches = [item for item in _get_items(session, "dashboard") if item.get("slug") == dashboard_slug or item.get("dashboard_title") == dashboard_title]
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


def _filter_state(column: str, value: str) -> dict:
    return {
        "extraFormData": {
            "adhoc_filters": [
                {
                    "clause": "WHERE",
                    "comparator": [value],
                    "expressionType": "SIMPLE",
                    "operator": "IN",
                    "subject": column,
                }
            ]
        },
        "filterState": {"value": [value], "label": value},
        "ownState": {},
    }


def _create_year_permalinks(session: requests.Session, dashboard_id: int) -> dict[str, str]:
    filter_ids = [
        "NATIVE_FILTER-tahun",
        "NATIVE_FILTER-prodi",
        "NATIVE_FILTER-iku",
        "NATIVE_FILTER-kegiatan",
        "NATIVE_FILTER-akun",
        "NATIVE_FILTER-quality",
    ]
    all_years_payload = {
        "dataMask": {filter_id: {"extraFormData": {"filters": []}, "filterState": {"value": None}, "ownState": {}} for filter_id in filter_ids},
        "activeTabs": [],
        "urlParams": [],
        "anchor": None,
    }
    all_years_response = session.post(
        f"{BASE_URL}/api/v1/dashboard/{dashboard_id}/permalink",
        json=all_years_payload,
        headers={"Origin": PUBLIC_BASE_URL},
        timeout=60,
    )
    all_years_response.raise_for_status()
    links: dict[str, str] = {"Semua": all_years_response.json()["url"]}
    for year in _filter_values("tahun"):
        value = str(year)
        payload = {
            "dataMask": {"NATIVE_FILTER-tahun": _filter_state("tahun", value)},
            "activeTabs": [],
            "urlParams": [],
            "anchor": None,
        }
        response = session.post(
            f"{BASE_URL}/api/v1/dashboard/{dashboard_id}/permalink",
            json=payload,
            headers={"Origin": PUBLIC_BASE_URL},
            timeout=60,
        )
        response.raise_for_status()
        links[value] = response.json()["url"]
    return links


def main() -> None:
    refresh_started_at = datetime.now(timezone.utc).isoformat()
    dataset_session_id = os.getenv("DATASET_SESSION_ID") or None
    pipeline_run_id = os.getenv("PIPELINE_RUN_ID") or None
    try:
        session = _login()
        database_id = _database_id(session)
        dataset_id = _dataset_id(session, database_id)
        total_anggaran = _metric("Total Anggaran", "SUM", "jumlah_weighted_iku")
        total_weighted = _metric("Total Weighted IKU", "SUM", "jumlah_weighted_iku")
        count_items = _metric("Jumlah Item", "COUNT_DISTINCT", "item_id")
        count_iku = _metric("Jumlah IKU", "COUNT_DISTINCT", "iku")
        count_kegiatan = _metric("Jumlah Kegiatan", "COUNT_DISTINCT", "kegiatan")
        chart_payloads = [
            _chart_payload(dataset_id, _chart_name("Executive KPI - Total Anggaran"), "big_number_total", {"metric": total_anggaran, "y_axis_format": ",d"}, {"metrics": [total_anggaran], "columns": []}),
            _chart_payload(dataset_id, _chart_name("Executive KPI - Total Weighted IKU"), "big_number_total", {"metric": total_weighted, "y_axis_format": ",d"}, {"metrics": [total_weighted], "columns": []}),
            _chart_payload(dataset_id, _chart_name("Executive KPI - Jumlah Item"), "big_number_total", {"metric": count_items, "y_axis_format": ",d"}, {"metrics": [count_items], "columns": []}),
            _chart_payload(dataset_id, _chart_name("Executive KPI - Jumlah IKU"), "big_number_total", {"metric": count_iku, "y_axis_format": ",d"}, {"metrics": [count_iku], "columns": []}),
            _chart_payload(dataset_id, _chart_name("Executive KPI - Jumlah Kegiatan"), "big_number_total", {"metric": count_kegiatan, "y_axis_format": ",d"}, {"metrics": [count_kegiatan], "columns": []}),
            _chart_payload(dataset_id, _chart_name("Ringkasan per Tahun"), "table", {"groupby": ["tahun"], "metrics": [total_anggaran, count_items], "page_length": 10}, {"metrics": [total_anggaran, count_items], "columns": ["tahun"], "orderby": [["tahun", True]], "row_limit": 10}),
            _chart_payload(dataset_id, _chart_name("Anggaran per Tahun"), "echarts_timeseries_bar", {"metrics": [total_anggaran], "x_axis": "tahun", "orientation": "vertical", "y_axis_format": ",d"}, {"metrics": [total_anggaran], "columns": ["tahun"], "orderby": [["tahun", True]]}),
            _chart_payload(dataset_id, _chart_name("Anggaran per IKU"), "echarts_timeseries_bar", {"metrics": [total_weighted], "x_axis": "iku", "orientation": "vertical", "y_axis_format": ",d"}, {"metrics": [total_weighted], "columns": ["iku"], "orderby": [[total_weighted, False]]}),
            _chart_payload(dataset_id, _chart_name("Cluster Kegiatan"), "treemap_v2", {"metric": total_anggaran, "groupby": ["iku", "kegiatan"], "label_type": "key_value"}, {"metrics": [total_anggaran], "columns": ["iku", "kegiatan"]}),
            _chart_payload(dataset_id, _chart_name("Komposisi Akun"), "echarts_timeseries_bar", {"metrics": [total_anggaran], "x_axis": "akun", "orientation": "horizontal", "y_axis_format": ",d", "row_limit": 25}, {"metrics": [total_anggaran], "columns": ["akun"], "orderby": [[total_anggaran, False]], "row_limit": 25}),
            _chart_payload(dataset_id, _chart_name("Anggaran per Akun"), "echarts_timeseries_bar", {"metrics": [total_anggaran], "x_axis": "akun", "orientation": "vertical", "y_axis_format": ",d"}, {"metrics": [total_anggaran], "columns": ["akun"], "orderby": [[total_anggaran, False]]}),
            _chart_payload(dataset_id, _chart_name("Mapping Quality"), "pie", {"metric": count_items, "groupby": ["mapping_status"], "label_type": "key_percent"}, {"metrics": [count_items], "columns": ["mapping_status"]}),
            _chart_payload(dataset_id, _chart_name("Detail Item Biaya"), "table", {"all_columns": ["tahun", "periode", "prodi", "iku", "kegiatan", "akun", "uraian_detail", "qty", "harga_satuan", "jumlah", "mapping_status", "data_quality_flag", "source_file", "source_sheet", "source_row"], "page_length": 25}, {"columns": ["tahun", "periode", "prodi", "iku", "kegiatan", "akun", "qty", "harga_satuan", "jumlah", "mapping_status", "data_quality_flag", "source_file", "source_sheet", "source_row"], "metrics": []}),
            _chart_payload(dataset_id, _chart_name("Validasi Rekap"), "table", {"all_columns": ["tahun", "periode", "source_file", "source_sheet", "jumlah", "data_quality_flag"], "page_length": 25}, {"columns": ["tahun", "periode", "source_file", "source_sheet", "jumlah", "data_quality_flag"], "metrics": []}),
        ]
        chart_ids = [_upsert_chart(session, payload) for payload in chart_payloads]
        dashboard_id = _upsert_dashboard(session, dataset_id, chart_ids)
        dashboard_urls_by_year = _create_year_permalinks(session, dashboard_id)
        default_dashboard_url = dashboard_urls_by_year.get("Semua") or f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/"
        result = {
            "status": "validated",
            "superset_api_status": "ready",
            "dashboard_mode": DASHBOARD_MODE,
            "database_id": database_id,
            "dataset_id": dataset_id,
            "table_name": TABLE_NAME,
            "dashboard_id": dashboard_id,
            "dashboard_title": _dashboard_title(),
            "dashboard_url": default_dashboard_url,
            "dashboard_canonical_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/",
            "default_filter_state": "all_years",
            "dashboard_urls_by_year": dashboard_urls_by_year,
            "chart_ids": chart_ids,
            "chart_count": len(chart_ids),
            "dataset_session_id": dataset_session_id,
            "pipeline_run_id": pipeline_run_id,
            "superset_refresh_started_at": refresh_started_at,
            "superset_refresh_finished_at": datetime.now(timezone.utc).isoformat(),
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
    if result.get("status") == "validated" and dataset_session_id and pipeline_run_id:
        manifest_path = OUTPUTS_DIR / "reports" / "pipeline_runs" / f"{pipeline_run_id}.json"
        try:
            manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("dataset_session_id") != dataset_session_id:
                raise RuntimeError("Identitas manifest Superset tidak cocok.")
            manifest.update({"superset_refresh_started_at": result["superset_refresh_started_at"], "superset_refresh_finished_at": result["superset_refresh_finished_at"]})
            temporary = manifest_path.with_suffix(".tmp")
            temporary.write_text(__import__("json").dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(manifest_path)
        except (OSError, ValueError, RuntimeError) as exc:
            result["status"] = "invalid"
            result["message"] = str(exc)
            write_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json", result)
        if result.get("status") == "validated":
            from portal_backend.services.superset_api import record_dashboard_verification

            verification = record_dashboard_verification(dataset_session_id, pipeline_run_id)
            result["dashboard_verification"] = verification
            if verification.get("status") != "validated":
                result["status"] = "invalid"
                result["message"] = verification.get("message") or "Query Superset belum memverifikasi run aktif."
            write_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json", result)
    print(result)


if __name__ == "__main__":
    main()
