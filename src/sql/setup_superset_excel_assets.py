from __future__ import annotations

import os
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.common.logging_utils import write_json
from src.common.paths import GENERATED_DIR, OUTPUTS_DIR
from src.gold.contract import DASHBOARD_FILTERS, FACT_COLUMNS, GOLD_METRICS


BASE_URL = os.getenv("SUPERSET_BASE_URL", "http://localhost:8089")
PUBLIC_BASE_URL = os.getenv("SUPERSET_PUBLIC_URL", "http://localhost:8089")
DATABASE_NAME = "Trino PostgreSQL Gold Keuangan"
TABLE_NAME = "fact_anggaran"
RECONCILIATION_TABLE_NAME = "vw_dashboard_reconciliation"
DASHBOARD_TITLE = "SILARAS SD - Dashboard Anggaran IKU"
DASHBOARD_SLUG = "dashboard-anggaran-iku-prodi"
DASHBOARD_MODE = os.getenv("SUPERSET_DASHBOARD_MODE", "update").strip().lower()
TARGET_DASHBOARD_ID = os.getenv("SUPERSET_DASHBOARD_ID", "").strip()

# Atribut teknis pipeline/QA yang disembunyikan dari tampilan Superset.
# Tabel faktual gold.fact_anggaran tetap utuh; kolom hanya dinonaktifkan di level dataset.
HIDDEN_COLUMNS = frozenset({"mapping_status", "data_quality_flag", "source_sheet", "source_row"})

# Nama fisik tetap mengikuti kontrak Gold agar query, pipeline, dan loader tidak
# berubah. Superset hanya memakai verbose_name ini sebagai label presentasi.
COLUMN_LABELS = {
    "item_id": "ID Item",
    "dataset_session_id": "Sesi Dataset",
    "run_id": "Run Pipeline",
    "tahun": "Tahun",
    "prodi": "Program Studi",
    "fakultas": "Fakultas",
    "kegiatan": "Kegiatan",
    "cluster_kegiatan": "Klaster Kegiatan",
    "akun": "Akun Belanja",
    "kode_akun": "Kode Akun",
    "nama_akun": "Nama Akun",
    "nama_akun_asli": "Nama Akun Asli",
    "iku": "IKU",
    "kode_iku": "Kode IKU",
    "nama_iku": "Nama IKU",
    "nomenklatur_path": "Jalur Nomenklatur",
    "uraian_detail": "Detail",
    "qty": "Kuantitas",
    "satuan": "Satuan",
    "harga_satuan": "Harga Satuan",
    "jumlah": "Jumlah Anggaran",
    "allocation_weight": "Bobot Alokasi",
    "jumlah_weighted_iku": "Alokasi Anggaran IKU",
    "mapping_status": "Status Mapping",
    "data_quality_flag": "Flag Kualitas Data",
    "source_file": "Sumber Data",
    "source_sheet": "Sheet Sumber",
    "source_row": "Baris Sumber",
    "source_role": "Peran Sumber",
    "row_type": "Jenis Baris",
    "quality_flags": "Catatan Kualitas",
    "created_at": "Waktu Dibuat",
    "total_detail": "Detail Total",
    "total_rekap": "Total Rekap",
    "selisih": "Selisih",
    "status": "Status",
}

DATASET_DISPLAY_NAME = "Data Anggaran RAB/IKU"

DETAIL_TABLE_COLUMNS = [
    "tahun",
    "prodi",
    "iku",
    "kegiatan",
    "akun",
    "uraian_detail",
    "qty",
    "harga_satuan",
    "jumlah",
    "source_file",
]

VALIDASI_TABLE_COLUMNS = ["tahun", "source_file", "total_detail", "total_rekap", "selisih", "status"]
DETAIL_MONEY_COLUMNS = ("harga_satuan", "jumlah")
VALIDASI_MONEY_COLUMNS = ("total_detail", "total_rekap", "selisih")
MONEY_D3_FORMAT = ",.0f"

SAVED_QUERY_DETAIL_SQL = """
SELECT tahun, prodi, fakultas, kegiatan, cluster_kegiatan, akun, kode_akun,
       nama_akun, nama_akun_asli, iku, kode_iku, nama_iku, uraian_detail, qty, satuan, harga_satuan,
       jumlah, allocation_weight, jumlah_weighted_iku, source_file
FROM fact_anggaran
ORDER BY tahun, prodi
"""

SAVED_QUERY_HIDDEN_COLUMNS_SQL = """
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'gold' AND table_name = 'fact_anggaran'
  AND column_name IN ('mapping_status', 'data_quality_flag', 'source_sheet', 'source_row')
ORDER BY column_name
"""

CHART_SPECS = [
    "kpi_total_anggaran",
    "kpi_jumlah_item",
    "kpi_jumlah_iku",
    "kpi_jumlah_kegiatan",
    "kpi_status_rekonsiliasi",
    "ringkasan_per_tahun",
    "anggaran_per_tahun",
    "anggaran_per_iku",
    "cluster_kegiatan",
    "komposisi_akun",
    "anggaran_per_akun",
    "detail_item_biaya",
    "validasi_rekap",
]

CHART_DISPLAY_NAMES = {
    "kpi_total_anggaran": "KPI Total Anggaran",
    "kpi_jumlah_item": "KPI Jumlah Item",
    "kpi_jumlah_iku": "KPI Jumlah IKU",
    "kpi_jumlah_kegiatan": "KPI Jumlah Kegiatan",
    "kpi_status_rekonsiliasi": "KPI Status Rekonsiliasi",
    "ringkasan_per_tahun": "Ringkasan per Tahun",
    "anggaran_per_tahun": "Anggaran per Tahun",
    "anggaran_per_iku": "Anggaran per IKU",
    "cluster_kegiatan": "Cluster Kegiatan",
    "komposisi_akun": "Komposisi Akun",
    "anggaran_per_akun": "Anggaran per Akun",
    "detail_item_biaya": "Detail Item Biaya",
    "validasi_rekap": "Validasi Rekap",
}

MANAGED_CHART_MARKER = "SILARAS_REGISTRY_KEY:"
LEGACY_MANAGED_CHART_MARKER = "silaras-managed:"
NEW_MANAGED_CHART_MARKER = "silaras-managed-new:"

CHART_REGISTRY = {
    "kpi_total_anggaran": {"key": "kpi_total_anggaran", "name": CHART_DISPLAY_NAMES["kpi_total_anggaran"], "dataset": "fact", "viz_type": "big_number_total", "metric_key": "total_anggaran", "groupby": [], "layout": {"width": 12, "height": 48}},
    "kpi_jumlah_item": {"key": "kpi_jumlah_item", "name": CHART_DISPLAY_NAMES["kpi_jumlah_item"], "dataset": "fact", "viz_type": "big_number_total", "metric_key": "jumlah_item", "groupby": [], "layout": {"width": 12, "height": 48}},
    "kpi_jumlah_iku": {"key": "kpi_jumlah_iku", "name": CHART_DISPLAY_NAMES["kpi_jumlah_iku"], "dataset": "fact", "viz_type": "big_number_total", "metric_key": "jumlah_iku", "groupby": [], "layout": {"width": 12, "height": 48}},
    "kpi_jumlah_kegiatan": {"key": "kpi_jumlah_kegiatan", "name": CHART_DISPLAY_NAMES["kpi_jumlah_kegiatan"], "dataset": "fact", "viz_type": "big_number_total", "metric_key": "jumlah_kegiatan", "groupby": [], "layout": {"width": 12, "height": 48}},
    "kpi_status_rekonsiliasi": {"key": "kpi_status_rekonsiliasi", "name": CHART_DISPLAY_NAMES["kpi_status_rekonsiliasi"], "dataset": "reconciliation", "viz_type": "table", "metric_key": None, "groupby": [], "layout": {"width": 12, "height": 48}},
    "ringkasan_per_tahun": {"key": "ringkasan_per_tahun", "name": CHART_DISPLAY_NAMES["ringkasan_per_tahun"], "dataset": "fact", "viz_type": "table", "metric_key": "total_anggaran", "groupby": ["tahun"], "layout": {"width": 12, "height": 48}},
    "anggaran_per_tahun": {"key": "anggaran_per_tahun", "name": CHART_DISPLAY_NAMES["anggaran_per_tahun"], "dataset": "fact", "viz_type": "echarts_timeseries_bar", "metric_key": "total_anggaran", "groupby": ["tahun"], "layout": {"width": 12, "height": 48}},
    "anggaran_per_iku": {"key": "anggaran_per_iku", "name": CHART_DISPLAY_NAMES["anggaran_per_iku"], "dataset": "fact", "viz_type": "echarts_timeseries_bar", "metric_key": "total_anggaran", "groupby": ["iku"], "layout": {"width": 12, "height": 48}},
    "cluster_kegiatan": {"key": "cluster_kegiatan", "name": CHART_DISPLAY_NAMES["cluster_kegiatan"], "dataset": "fact", "viz_type": "treemap_v2", "metric_key": "total_anggaran", "groupby": ["iku", "kegiatan"], "layout": {"width": 12, "height": 48}},
    "komposisi_akun": {"key": "komposisi_akun", "name": CHART_DISPLAY_NAMES["komposisi_akun"], "dataset": "fact", "viz_type": "echarts_timeseries_bar", "metric_key": "total_anggaran", "groupby": ["akun"], "layout": {"width": 12, "height": 48}},
    "anggaran_per_akun": {"key": "anggaran_per_akun", "name": CHART_DISPLAY_NAMES["anggaran_per_akun"], "dataset": "fact", "viz_type": "echarts_timeseries_bar", "metric_key": "total_anggaran", "groupby": ["akun"], "layout": {"width": 12, "height": 48}},
    "detail_item_biaya": {"key": "detail_item_biaya", "name": CHART_DISPLAY_NAMES["detail_item_biaya"], "dataset": "fact", "viz_type": "table", "metric_key": None, "groupby": [], "layout": {"width": 12, "height": 48}},
    "validasi_rekap": {"key": "validasi_rekap", "name": CHART_DISPLAY_NAMES["validasi_rekap"], "dataset": "reconciliation", "viz_type": "table", "metric_key": None, "groupby": [], "layout": {"width": 12, "height": 48}},
}


DASHBOARD_INSTANCE_NUMBER: int | None = None
_configured_dashboard_number = os.getenv("DASHBOARD_INSTANCE_NUMBER", "").strip()
if _configured_dashboard_number.isdigit() and int(_configured_dashboard_number) > 0:
    DASHBOARD_INSTANCE_NUMBER = int(_configured_dashboard_number)


def _next_dashboard_instance_number(session: requests.Session) -> int:
    pattern = re.compile(rf"^{re.escape(DASHBOARD_TITLE)}(?:\s+(\d+))?$")
    numbers = []
    for dashboard in _get_items(session, "dashboard"):
        match = pattern.fullmatch(str(dashboard.get("dashboard_title") or "").strip())
        if match and match.group(1):
            numbers.append(int(match.group(1)))
    return max(numbers, default=0) + 1


def _prepare_new_dashboard_instance(session: requests.Session) -> int | None:
    global DASHBOARD_INSTANCE_NUMBER
    if DASHBOARD_MODE != "new":
        return None
    if DASHBOARD_INSTANCE_NUMBER is None:
        DASHBOARD_INSTANCE_NUMBER = _next_dashboard_instance_number(session)
    return DASHBOARD_INSTANCE_NUMBER


def _dashboard_title() -> str:
    if DASHBOARD_MODE == "new":
        return f"{DASHBOARD_TITLE} {DASHBOARD_INSTANCE_NUMBER or 1}"
    return DASHBOARD_TITLE


def _dashboard_slug() -> str:
    if DASHBOARD_MODE == "new":
        return f"{DASHBOARD_SLUG}-{DASHBOARD_INSTANCE_NUMBER or 1}"
    return DASHBOARD_SLUG


def _chart_name(name: str) -> str:
    if DASHBOARD_MODE == "new":
        return f"{name} {DASHBOARD_INSTANCE_NUMBER or 1}"
    return name


def _chart_registry_marker(registry_key: str) -> str:
    if DASHBOARD_MODE == "new":
        return f"{NEW_MANAGED_CHART_MARKER}{DASHBOARD_INSTANCE_NUMBER or 1}:{registry_key}"
    return f"{MANAGED_CHART_MARKER}{registry_key}"


def _resolve_pipeline_identity() -> tuple[str, str]:
    active_dataset_path = OUTPUTS_DIR / "reports" / "active_excel_lakehouse_dataset.json"
    try:
        active_dataset = json.loads(active_dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Dataset aktif belum tersedia; Superset tidak dijalankan.") from exc
    if str(active_dataset.get("status") or "").lower() != "committed" or not active_dataset.get("files"):
        raise RuntimeError("Dataset aktif belum berstatus COMMITTED; Superset tidak dijalankan.")
    active_session_id = str(active_dataset.get("dataset_session_id") or active_dataset.get("dataset_id") or "").strip()
    if not active_session_id:
        raise RuntimeError("Dataset aktif tidak memiliki dataset_session_id.")

    env_dataset_session_id = str(os.getenv("DATASET_SESSION_ID") or "").strip()
    env_pipeline_run_id = str(os.getenv("PIPELINE_RUN_ID") or "").strip()
    if env_dataset_session_id and env_pipeline_run_id:
        if env_dataset_session_id != active_session_id:
            raise RuntimeError("Identitas Superset berbeda dari dataset aktif.")
        return env_dataset_session_id, env_pipeline_run_id
    if env_dataset_session_id or env_pipeline_run_id:
        raise RuntimeError("DATASET_SESSION_ID dan PIPELINE_RUN_ID harus diisi berpasangan.")

    manifest_path = OUTPUTS_DIR / "reports" / "active_gold_run.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Identitas Gold aktif belum tersedia; Superset tidak dijalankan.") from exc
    if str(manifest.get("status") or "").upper() != "PUBLISHED":
        raise RuntimeError("Gold aktif belum berstatus PUBLISHED; Superset tidak dijalankan.")
    dataset_session_id = str(manifest.get("dataset_session_id") or "").strip()
    pipeline_run_id = str(manifest.get("pipeline_run_id") or "").strip()
    if not dataset_session_id or not pipeline_run_id:
        raise RuntimeError("Gold aktif tidak memiliki dataset_session_id dan pipeline_run_id.")
    if dataset_session_id != active_session_id:
        raise RuntimeError("Gold aktif berbeda dari dataset aktif; Superset tidak dijalankan.")
    return dataset_session_id, pipeline_run_id


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
    response = session.get(f"{BASE_URL}/api/v1/{resource}/?q=(page:0,page_size:500)", timeout=30)
    response.raise_for_status()
    return response.json().get("result", [])


def _database_id(session: requests.Session) -> int:
    requested_id = os.getenv("SUPERSET_DATABASE_ID", "").strip()
    if requested_id.isdigit():
        for item in _get_items(session, "database"):
            if str(item.get("id")) == requested_id:
                return int(item["id"])
        raise RuntimeError(f"Superset database id {requested_id} tidak ditemukan.")
    requested_name = os.getenv("SUPERSET_DATABASE_NAME", "").strip() or DATABASE_NAME
    for item in _get_items(session, "database"):
        if item.get("database_name") == requested_name:
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


def _dataset_id(session: requests.Session, database_id: int, table_name: str = TABLE_NAME, display_name: str = DATASET_DISPLAY_NAME) -> int:
    datasets = session.get(f"{BASE_URL}/api/v1/dataset/?q=(filters:!((col:table_name,opr:eq,value:{table_name})))", timeout=30)
    datasets.raise_for_status()
    result = datasets.json().get("result", [])
    if result:
        dataset_id = int(result[0]["id"])
        update = session.put(
            f"{BASE_URL}/api/v1/dataset/{dataset_id}",
            json={
                "database_id": database_id,
                "catalog": "postgres",
                "schema": "gold",
                "table_name": table_name,
                "description": display_name,
            },
            timeout=60,
        )
        update.raise_for_status()
    else:
        payload = {
            "database": database_id,
            "catalog": "postgres",
            "schema": "gold",
            "table_name": table_name,
        }
        response = session.post(f"{BASE_URL}/api/v1/dataset/", json=payload, timeout=60)
        if response.status_code not in {200, 201, 422}:
            response.raise_for_status()
        raw_dataset_id = response.json().get("id") or response.json().get("result", {}).get("id")
        if raw_dataset_id is None:
            raise RuntimeError(f"Superset dataset {table_name!r} was not created or found")
        dataset_id = int(raw_dataset_id)
        update = session.put(
            f"{BASE_URL}/api/v1/dataset/{dataset_id}",
            json={
                "database_id": database_id,
                "catalog": "postgres",
                "schema": "gold",
                "table_name": table_name,
                "description": display_name,
            },
            timeout=60,
        )
        update.raise_for_status()
    refresh = session.put(f"{BASE_URL}/api/v1/dataset/{dataset_id}/refresh", timeout=60)
    refresh.raise_for_status()
    return dataset_id


def _dataset_column_payload(column: dict) -> dict:
    name = str(column.get("column_name") or "").strip()
    if not name:
        raise ValueError("Kolom Superset harus memiliki column_name.")
    return {
        "id": column.get("id"),
        "column_name": name,
        "verbose_name": COLUMN_LABELS.get(name, name.replace("_", " ").title()),
        "is_active": name not in HIDDEN_COLUMNS,
    }


def _remove_stale_dataset_columns(session: requests.Session, dataset_id: int) -> list[str]:
    """Remove Superset metadata columns no longer present in canonical Gold."""

    response = session.get(f"{BASE_URL}/api/v1/dataset/{dataset_id}", timeout=60)
    response.raise_for_status()
    columns = (response.json().get("result") or {}).get("columns") or []
    stale = [
        column
        for column in columns
        if str(column.get("column_name") or "").strip() not in FACT_COLUMNS
    ]
    removed: list[str] = []
    for column in stale:
        column_id = column.get("id")
        column_name = str(column.get("column_name") or "").strip()
        if not column_id or not column_name:
            continue
        delete = session.delete(
            f"{BASE_URL}/api/v1/dataset/{dataset_id}/column/{column_id}",
            timeout=60,
        )
        if delete.status_code not in {200, 204, 404}:
            delete.raise_for_status()
        removed.append(column_name)
    return removed


def _deactivate_hidden_columns(session: requests.Session, dataset_id: int) -> list[str]:
    response = session.get(f"{BASE_URL}/api/v1/dataset/{dataset_id}", timeout=60)
    response.raise_for_status()
    columns = (response.json().get("result") or {}).get("columns") or []
    payload_columns: list[dict] = []
    deactivated: list[str] = []
    for column in columns:
        name = column.get("column_name")
        if not name:
            continue
        is_active = name not in HIDDEN_COLUMNS
        if not is_active:
            deactivated.append(name)
        payload_columns.append(_dataset_column_payload(column))
    if payload_columns:
        update = session.put(
            f"{BASE_URL}/api/v1/dataset/{dataset_id}",
            json={"columns": payload_columns},
            timeout=60,
        )
        if update.status_code not in {200, 201}:
            update.raise_for_status()
    return deactivated


def _upsert_saved_query(session: requests.Session, database_id: int, label: str, sql: str, description: str) -> int:
    matches = [item for item in _get_items(session, "saved_query") if item.get("label") == label]
    payload = {"db_id": database_id, "schema": "gold", "label": label, "sql": sql, "description": description}
    if matches:
        query_id = int(sorted(matches, key=lambda item: int(item["id"]))[0]["id"])
        response = session.put(f"{BASE_URL}/api/v1/saved_query/{query_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/saved_query/", json=payload, timeout=60)
        query_id = None
    response.raise_for_status()
    return int(response.json().get("id") or response.json().get("result", {}).get("id") or query_id)


def _clean_stale_dashboards(session: requests.Session, dataset_id: int) -> dict:
    import json

    cleaned_dashboards: list[int] = []
    cleaned_charts: list[int] = []
    removed_quality_filters = 0
    for dashboard in _get_items(session, "dashboard"):
        dashboard_title = str(dashboard.get("dashboard_title") or "")
        dashboard_slug = str(dashboard.get("slug") or "")
        managed_dashboard = (
            TARGET_DASHBOARD_ID.isdigit() and str(dashboard.get("id")) == TARGET_DASHBOARD_ID
        ) or dashboard_title.startswith(DASHBOARD_TITLE) or dashboard_slug.startswith(DASHBOARD_SLUG)
        if not managed_dashboard:
            continue
        detail = session.get(f"{BASE_URL}/api/v1/dashboard/{dashboard['id']}", timeout=60)
        detail.raise_for_status()
        result = detail.json().get("result") or {}
        position = result.get("position_json") or {}
        metadata = result.get("json_metadata") or {}
        if isinstance(position, str):
            position = json.loads(position)
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        grid = position.get("GRID_ID") or {}
        grid_children = list(grid.get("children") or [])
        row_of = {}
        for node_id, node in position.items():
            if isinstance(node, dict) and node.get("type") == "ROW":
                for child in node.get("children") or []:
                    row_of[child] = node_id

        dashboard_changed = False
        for node_id, node in list(position.items()):
            if not isinstance(node, dict) or node.get("type") != "CHART":
                continue
            chart_id = int(node.get("meta", {}).get("chartId"))
            chart_response = session.get(f"{BASE_URL}/api/v1/chart/{chart_id}", timeout=60)
            if chart_response.status_code != 200:
                continue
            chart = chart_response.json().get("result") or {}
            if not str(chart.get("description") or "").startswith(MANAGED_CHART_MARKER):
                continue
            name = chart.get("slice_name") or ""
            viz_type = chart.get("viz_type") or ""
            params: dict = {}
            if chart.get("params"):
                try:
                    params = json.loads(chart["params"]) if isinstance(chart["params"], str) else chart["params"]
                except ValueError:
                    params = {}
            groupby = params.get("groupby") or []
            if viz_type == "pie" and "mapping_status" in groupby:
                position.pop(node_id, None)
                row_id = row_of.get(node_id)
                if row_id:
                    position.pop(row_id, None)
                    if row_id in grid_children:
                        grid_children.remove(row_id)
                dashboard_changed = True
                continue
            if viz_type == "table" and chart.get("datasource_id") == dataset_id:
                new_columns = None
                if "Detail Item Biaya" in name:
                    new_columns = DETAIL_TABLE_COLUMNS
                elif "Validasi Rekap" in name:
                    new_columns = VALIDASI_TABLE_COLUMNS
                if new_columns is not None and (params.get("all_columns") or []) != new_columns:
                    payload = _chart_payload(dataset_id, name, "table", {"all_columns": new_columns, "page_length": 25}, {"columns": new_columns, "metrics": []})
                    session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60).raise_for_status()
                    cleaned_charts.append(chart_id)

        filters = metadata.get("native_filter_configuration") or []
        kept_filters = [nf for nf in filters if not (isinstance(nf, dict) and nf.get("groupby") == "data_quality_flag")]
        if len(kept_filters) != len(filters):
            metadata["native_filter_configuration"] = kept_filters
            removed_quality_filters += len(filters) - len(kept_filters)
            dashboard_changed = True

        if dashboard_changed:
            grid["children"] = grid_children
            position["GRID_ID"] = grid
            session.put(
                f"{BASE_URL}/api/v1/dashboard/{dashboard['id']}",
                json={"position_json": json.dumps(position), "json_metadata": json.dumps(metadata)},
                timeout=60,
            ).raise_for_status()
            cleaned_dashboards.append(int(dashboard["id"]))
    return {
        "cleaned_dashboards": cleaned_dashboards,
        "cleaned_charts": cleaned_charts,
        "removed_quality_filters": removed_quality_filters,
    }


def _metric(label: str, aggregate: str, column: str) -> dict:
    return {
        "aggregate": aggregate,
        "column": {"column_name": column},
        "expressionType": "SIMPLE",
        "label": label,
        "optionName": f"metric_{label.lower().replace(' ', '_')}",
    }


def _chart_payload(dataset_id: int, name: str, viz_type: str, form_data: dict, query: dict, registry_key: str | None = None) -> dict:
    form_data = {
        "datasource": f"{dataset_id}__table",
        "viz_type": viz_type,
        "row_limit": 10000,
        "adhoc_filters": [],
        "time_range": "No filter",
        **form_data,
    }
    query = {"filters": [], "extras": {"having": "", "where": ""}, "applied_time_extras": {}, "annotation_layers": [], "row_limit": 10000, "series_limit": 0, **query}
    payload = {
        "slice_name": name,
        "viz_type": viz_type,
        "datasource_id": dataset_id,
        "datasource_type": "table",
        "params": __import__("json").dumps(form_data),
        "query_context": __import__("json").dumps({"datasource": {"id": dataset_id, "type": "table"}, "force": False, "queries": [query], "form_data": form_data, "result_format": "json", "result_type": "full"}),
    }
    if registry_key:
        payload["description"] = _chart_registry_marker(registry_key)
    return payload


def _money_column_config(columns: tuple[str, ...]) -> dict[str, dict[str, str]]:
    return {column: {"d3NumberFormat": MONEY_D3_FORMAT} for column in columns}


def _upsert_chart(session: requests.Session, payload: dict) -> int:
    managed_description = payload.get("description")
    charts = _get_items(session, "chart")
    if DASHBOARD_MODE == "new":
        matches = [item for item in charts if item.get("description") == managed_description]
        if matches:
            chart_id = int(sorted(matches, key=lambda item: int(item["id"]))[0]["id"])
            response = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60)
        else:
            response = session.post(f"{BASE_URL}/api/v1/chart/", json=payload, timeout=60)
            chart_id = None
        response.raise_for_status()
        return int(response.json().get("id") or response.json().get("result", {}).get("id") or chart_id)
    registry_key = (
        str(managed_description)[len(MANAGED_CHART_MARKER):]
        if str(managed_description).startswith(MANAGED_CHART_MARKER)
        else ""
    )
    managed_descriptions = {
        value
        for value in (
            managed_description,
            f"{LEGACY_MANAGED_CHART_MARKER}{registry_key}" if registry_key else None,
        )
        if value
    }
    matches = [item for item in charts if item.get("description") in managed_descriptions]
    if not matches:
        matches = [item for item in charts if item.get("slice_name") == payload["slice_name"] and str(item.get("slice_name", "")).startswith("SILARAS |")]
    if not matches and registry_key:
        legacy_name = CHART_DISPLAY_NAMES.get(registry_key)
        legacy_description = f"{LEGACY_MANAGED_CHART_MARKER}{registry_key}"
        candidates = [item for item in charts if item.get("slice_name") == legacy_name]
        for candidate in candidates:
            detail = session.get(f"{BASE_URL}/api/v1/chart/{candidate['id']}", timeout=60)
            if detail.status_code == 200 and (detail.json().get("result") or {}).get("description") == legacy_description:
                matches.append(candidate)
    if matches:
        chart_id = int(sorted(matches, key=lambda item: int(item["id"]))[0]["id"])
        response = session.put(f"{BASE_URL}/api/v1/chart/{chart_id}", json=payload, timeout=60)
    else:
        response = session.post(f"{BASE_URL}/api/v1/chart/", json=payload, timeout=60)
        chart_id = None
    response.raise_for_status()
    return int(response.json().get("id") or response.json().get("result", {}).get("id") or chart_id)


def _registry_metric(key: str) -> dict:
    metric = next(item for item in GOLD_METRICS if item["key"] == key)
    if metric["aggregation"] == "STATUS":
        raise ValueError(f"Metric status tidak dapat dijumlahkan: {key}")
    return _metric(metric["label"], metric["aggregation"], metric["column"])


def _registry_chart_payload(key: str, fact_dataset_id: int, reconciliation_dataset_id: int) -> dict:
    name = _chart_name(CHART_REGISTRY[key]["name"])
    total = _registry_metric("total_anggaran")
    count_items = _registry_metric("jumlah_item")
    count_iku = _registry_metric("jumlah_iku")
    count_kegiatan = _registry_metric("jumlah_kegiatan")
    if key == "kpi_total_anggaran":
        return _chart_payload(fact_dataset_id, name, "big_number_total", {"metric": total, "y_axis_format": MONEY_D3_FORMAT}, {"metrics": [total], "columns": []}, key)
    if key == "kpi_jumlah_item":
        return _chart_payload(fact_dataset_id, name, "big_number_total", {"metric": count_items, "y_axis_format": ",d"}, {"metrics": [count_items], "columns": []}, key)
    if key == "kpi_jumlah_iku":
        return _chart_payload(fact_dataset_id, name, "big_number_total", {"metric": count_iku, "y_axis_format": ",d"}, {"metrics": [count_iku], "columns": []}, key)
    if key == "kpi_jumlah_kegiatan":
        return _chart_payload(fact_dataset_id, name, "big_number_total", {"metric": count_kegiatan, "y_axis_format": ",d"}, {"metrics": [count_kegiatan], "columns": []}, key)
    if key == "kpi_status_rekonsiliasi":
        return _chart_payload(reconciliation_dataset_id, name, "table", {"all_columns": ["status"], "page_length": 5}, {"columns": ["status"], "metrics": []}, key)
    if key == "ringkasan_per_tahun":
        return _chart_payload(fact_dataset_id, name, "table", {"groupby": ["tahun"], "metrics": [total, count_items], "page_length": 10, "show_cell_bars": False}, {"metrics": [total, count_items], "columns": ["tahun"], "orderby": [["tahun", True]], "row_limit": 10}, key)
    if key == "anggaran_per_tahun":
        return _chart_payload(fact_dataset_id, name, "echarts_timeseries_bar", {"metrics": [total], "x_axis": "tahun", "orientation": "vertical", "y_axis_format": MONEY_D3_FORMAT}, {"metrics": [total], "columns": ["tahun"], "orderby": [["tahun", True]]}, key)
    if key == "anggaran_per_iku":
        return _chart_payload(fact_dataset_id, name, "echarts_timeseries_bar", {"metrics": [total], "x_axis": "iku", "orientation": "vertical", "y_axis_format": MONEY_D3_FORMAT}, {"metrics": [total], "columns": ["iku"], "orderby": [[total, False]]}, key)
    if key == "cluster_kegiatan":
        return _chart_payload(fact_dataset_id, name, "treemap_v2", {"metric": total, "groupby": ["iku", "kegiatan"], "label_type": "key_value"}, {"metrics": [total], "columns": ["iku", "kegiatan"]}, key)
    if key == "komposisi_akun":
        return _chart_payload(fact_dataset_id, name, "echarts_timeseries_bar", {"metrics": [total], "x_axis": "akun", "orientation": "horizontal", "y_axis_format": MONEY_D3_FORMAT, "row_limit": 25}, {"metrics": [total], "columns": ["akun"], "orderby": [[total, False]], "row_limit": 25}, key)
    if key == "anggaran_per_akun":
        return _chart_payload(fact_dataset_id, name, "echarts_timeseries_bar", {"metrics": [total], "x_axis": "akun", "orientation": "vertical", "y_axis_format": MONEY_D3_FORMAT}, {"metrics": [total], "columns": ["akun"], "orderby": [[total, False]]}, key)
    if key == "detail_item_biaya":
        return _chart_payload(fact_dataset_id, name, "table", {"all_columns": DETAIL_TABLE_COLUMNS, "column_config": _money_column_config(DETAIL_MONEY_COLUMNS), "page_length": 25}, {"columns": DETAIL_TABLE_COLUMNS, "metrics": []}, key)
    if key == "validasi_rekap":
        return _chart_payload(reconciliation_dataset_id, name, "table", {"all_columns": VALIDASI_TABLE_COLUMNS, "column_config": _money_column_config(VALIDASI_MONEY_COLUMNS), "page_length": 25}, {"columns": VALIDASI_TABLE_COLUMNS, "metrics": []}, key)
    raise KeyError(key)


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


def _native_filters(dataset_id: int, chart_ids: list[int], excluded_chart_ids: set[int] | None = None) -> list[dict]:
    excluded = excluded_chart_ids or set()
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
            "chartsInScope": [chart_id for chart_id in chart_ids if chart_id not in excluded],
            "type": "NATIVE_FILTER",
            "controlValues": {
                "enableEmptyFilter": False,
                "multiSelect": multi_select,
                "searchAllOptions": True,
                "defaultToFirstItem": False,
                "inverseSelection": False,
            },
        }
    labels = {"tahun": "Tahun", "prodi": "Prodi", "iku": "IKU", "kegiatan": "Kegiatan", "akun": "Akun"}
    return [nf(f"NATIVE_FILTER-{column}", labels[column], column) for column in DASHBOARD_FILTERS]


def _target_dashboard_id(session: requests.Session) -> int | None:
    if DASHBOARD_MODE == "new":
        return None
    if not TARGET_DASHBOARD_ID.isdigit():
        return None
    target = int(TARGET_DASHBOARD_ID)
    existing = {int(item["id"]) for item in _get_items(session, "dashboard")}
    return target if target in existing else None


def _upsert_dashboard(session: requests.Session, dataset_id: int, chart_ids: list[int], excluded_chart_ids: set[int] | None = None) -> int:
    import json

    dashboard_title = _dashboard_title()
    dashboard_slug = _dashboard_slug()
    payload = {
        "dashboard_title": dashboard_title,
        "slug": dashboard_slug,
        "published": True,
        "json_metadata": json.dumps({
            "native_filter_configuration": _native_filters(dataset_id, chart_ids, excluded_chart_ids),
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
    target = _target_dashboard_id(session)
    if target is not None:
        dashboard_id = target
        response = session.put(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", json=payload, timeout=60)
        response.raise_for_status()
    else:
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


def _detach_stale_managed_charts(session: requests.Session, dashboard_id: int, active_keys: list[str]) -> int:
    """Detach obsolete registry charts from one managed dashboard only."""

    if DASHBOARD_MODE == "new":
        return 0

    import json

    response = session.get(f"{BASE_URL}/api/v1/dashboard/{dashboard_id}", timeout=60)
    response.raise_for_status()
    result = response.json().get("result") or {}
    position = result.get("position_json") or {}
    if isinstance(position, str):
        position = json.loads(position)
    active = set(active_keys)
    row_of: dict[str, str] = {}
    for node_id, node in position.items():
        if isinstance(node, dict) and node.get("type") == "ROW":
            for child in node.get("children") or []:
                row_of[child] = node_id
    removed = 0
    grid_children = list((position.get("GRID_ID") or {}).get("children") or [])
    for node_id, node in list(position.items()):
        if not isinstance(node, dict) or node.get("type") != "CHART":
            continue
        chart_id = node.get("meta", {}).get("chartId")
        if not chart_id:
            continue
        chart_response = session.get(f"{BASE_URL}/api/v1/chart/{chart_id}", timeout=60)
        if chart_response.status_code != 200:
            continue
        chart = chart_response.json().get("result") or {}
        description = str(chart.get("description") or "")
        if not description.startswith(MANAGED_CHART_MARKER):
            continue
        key = description[len(MANAGED_CHART_MARKER):]
        if key in active:
            continue
        position.pop(node_id, None)
        row_id = row_of.get(node_id)
        if row_id:
            position.pop(row_id, None)
            if row_id in grid_children:
                grid_children.remove(row_id)
        removed += 1
    if removed:
        position.setdefault("GRID_ID", {})["children"] = grid_children
        session.put(
            f"{BASE_URL}/api/v1/dashboard/{dashboard_id}",
            json={"position_json": json.dumps(position)},
            timeout=60,
        ).raise_for_status()
    return removed


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


def _write_superset_reports(result: dict) -> None:
    write_json(OUTPUTS_DIR / "reports" / "superset_excel_dashboard.json", result)
    write_json(OUTPUTS_DIR / "reports" / "superset_excel_assets.json", result)


def main() -> dict:
    refresh_started_at = datetime.now(timezone.utc).isoformat()
    try:
        dataset_session_id, pipeline_run_id = _resolve_pipeline_identity()
    except RuntimeError as exc:
        result = {
            "status": "invalid",
            "superset_api_status": "not_run",
            "table_name": TABLE_NAME,
            "dashboard_title": _dashboard_title(),
            "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/",
            "message": str(exc),
        }
        _write_superset_reports(result)
        print(result)
        return result

    try:
        session = _login()
        _prepare_new_dashboard_instance(session)
        database_id = _database_id(session)
        dataset_id = _dataset_id(session, database_id, TABLE_NAME, DATASET_DISPLAY_NAME)
        reconciliation_dataset_id = _dataset_id(session, database_id, RECONCILIATION_TABLE_NAME, "Status Rekonsiliasi Anggaran")
        stale_columns_removed = _remove_stale_dataset_columns(session, dataset_id)
        hidden_deactivated = _deactivate_hidden_columns(session, dataset_id)
        reconciliation_labels_updated = _deactivate_hidden_columns(session, reconciliation_dataset_id)
        chart_ids = [
            _upsert_chart(session, _registry_chart_payload(key, dataset_id, reconciliation_dataset_id))
            for key in CHART_SPECS
        ]
        desired_chart_count = len(CHART_SPECS)
        attached_chart_count = len(chart_ids)
        if desired_chart_count != attached_chart_count or attached_chart_count != 13:
            raise RuntimeError(f"Registry chart tidak valid: desired={desired_chart_count}, attached={attached_chart_count}")
        reconciliation_chart_ids = {
            chart_ids[CHART_SPECS.index("kpi_status_rekonsiliasi")],
            chart_ids[CHART_SPECS.index("validasi_rekap")],
        }
        dashboard_id = _upsert_dashboard(session, dataset_id, chart_ids, excluded_chart_ids=reconciliation_chart_ids)
        detached_chart_count = _detach_stale_managed_charts(session, dashboard_id, CHART_SPECS)
        dashboard_urls_by_year = _create_year_permalinks(session, dashboard_id)
        saved_query_ids = [
            _upsert_saved_query(
                session,
                database_id,
                "SILARAS - Detail Item Biaya (tanpa kolom teknis)",
                SAVED_QUERY_DETAIL_SQL,
                "Query cek data faktual gold.fact_anggaran tanpa atribut teknis mapping_status, data_quality_flag, source_sheet, source_row.",
            ),
            _upsert_saved_query(
                session,
                database_id,
                "SILARAS - Cek Kolom Teknis (audit)",
                SAVED_QUERY_HIDDEN_COLUMNS_SQL,
                "Audit: kolom teknis masih ada di tabel gold.fact_anggaran tetapi disembunyikan dari dataset Superset.",
            ),
        ]
        default_dashboard_url = dashboard_urls_by_year.get("Semua") or f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/"
        result = {
            "status": "validated",
            "superset_api_status": "ready",
            "dashboard_mode": DASHBOARD_MODE,
            "database_id": database_id,
            "dataset_id": dataset_id,
            "reconciliation_dataset_id": reconciliation_dataset_id,
            "table_name": TABLE_NAME,
            "dataset_display_name": DATASET_DISPLAY_NAME,
            "column_labels": COLUMN_LABELS,
            "dashboard_id": dashboard_id,
            "dashboard_target": "explicit_id" if DASHBOARD_MODE != "new" and TARGET_DASHBOARD_ID.isdigit() and str(dashboard_id) == TARGET_DASHBOARD_ID else "slug_or_create",
            "dashboard_title": _dashboard_title(),
            "dashboard_url": default_dashboard_url,
            "dashboard_canonical_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/",
            "default_filter_state": "all_years",
            "dashboard_urls_by_year": dashboard_urls_by_year,
            "chart_ids": chart_ids,
            "chart_count": len(chart_ids),
            "desired_chart_count": desired_chart_count,
            "attached_chart_count": attached_chart_count,
            "detached_chart_count": detached_chart_count,
            "chart_registry": CHART_SPECS,
            "hidden_columns": sorted(HIDDEN_COLUMNS),
            "hidden_columns_deactivated": hidden_deactivated,
            "reconciliation_labels_updated": reconciliation_labels_updated,
            "stale_columns_removed": stale_columns_removed,
            "saved_query_ids": saved_query_ids,
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
            "dashboard_title": _dashboard_title(),
            "dashboard_url": f"{PUBLIC_BASE_URL}/superset/dashboard/{_dashboard_slug()}/",
            "dataset_session_id": dataset_session_id,
            "pipeline_run_id": pipeline_run_id,
            "message": str(exc),
        }

    if result.get("status") == "validated":
        manifest_path = OUTPUTS_DIR / "reports" / "pipeline_runs" / f"{pipeline_run_id}.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                manifest.get("dataset_session_id") != dataset_session_id
                or manifest.get("pipeline_run_id") != pipeline_run_id
            ):
                raise RuntimeError("Identitas manifest Superset tidak cocok.")
            manifest.update(
                {
                    "superset_refresh_started_at": result["superset_refresh_started_at"],
                    "superset_refresh_finished_at": result["superset_refresh_finished_at"],
                }
            )
            temporary = manifest_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(manifest_path)
        except (OSError, ValueError, RuntimeError) as exc:
            result["status"] = "invalid"
            result["message"] = str(exc)

    if result.get("status") == "validated":
        try:
            from portal_backend.services.superset_api import record_dashboard_verification

            verification = record_dashboard_verification(dataset_session_id, pipeline_run_id)
            result["dashboard_verification"] = verification
            if verification.get("status") != "validated":
                result["status"] = "invalid"
                result["message"] = verification.get("message") or "Query Superset belum memverifikasi run aktif."
        except Exception as exc:
            result["status"] = "invalid"
            result["message"] = str(exc)

    _write_superset_reports(result)
    print(result)
    return result


if __name__ == "__main__":
    raise SystemExit(0 if main().get("status") == "validated" else 1)
