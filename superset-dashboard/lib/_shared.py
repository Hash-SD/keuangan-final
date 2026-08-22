from __future__ import annotations

import base64
import json
import os
import re
import threading
import time
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Superset connection (server-side only, never exposed to the browser)
# ---------------------------------------------------------------------------
USERNAME = os.getenv("SUPERSET_USERNAME", "admin")
PASSWORD = os.getenv("SUPERSET_PASSWORD", "admin")


def superset_base_url() -> str:
    explicit = os.getenv("SUPERSET_BASE_URL")
    if explicit:
        return explicit.rstrip("/")
    host = os.getenv("SUPERSET_HOST", "localhost")
    port = os.getenv("SUPERSET_PORT", "8089")
    return f"http://{host}:{port}".rstrip("/")


def _timeout() -> float:
    return float(os.getenv("SUPERSET_API_TIMEOUT_SECONDS", "12.0"))


# ---------------------------------------------------------------------------
# Spec normalisation helpers
# ---------------------------------------------------------------------------
_CURRENCY = "currency"
_INTEGER = "integer"


def _datasource_from_params(params: dict[str, Any]) -> dict[str, Any]:
    raw = params.get("datasource") or ""
    parts = str(raw).split("__")
    ds_id = int(parts[0]) if parts and parts[0].isdigit() else 2
    ds_type = parts[1] if len(parts) > 1 else "table"
    return {"id": ds_id, "type": ds_type}


def _guess_format(metric: dict[str, Any] | None) -> str:
    if not metric:
        return _INTEGER
    col = (metric.get("column") or {}).get("column_name", "")
    agg = str(metric.get("aggregate", "")).upper()
    if any(token in col for token in ("jumlah_item", "jumlah_iku", "jumlah_kegiatan", "count", "status")):
        return _INTEGER
    if "jumlah" in col or "weighted" in col or "harga" in col or "total" in col:
        return _CURRENCY
    if agg in ("SUM", "AVG") and col not in ("qty", "source_row"):
        return _CURRENCY
    return _INTEGER


def _spec_from_chart(chart: dict[str, Any]) -> dict[str, Any]:
    """Build a renderer spec from a Superset chart detail object."""
    params = json.loads(chart.get("params") or "{}")
    viz = chart.get("viz_type") or params.get("viz_type") or "table"
    datasource = _datasource_from_params(params)
    slice_name = chart.get("slice_name") or params.get("slice_name") or f"Chart #{chart.get('id')}"

    spec: dict[str, Any] = {
        "id": int(chart["id"]),
        "slice_name": slice_name,
        "viz_type": viz,
        "datasource": datasource,
        "row_limit": int(params.get("row_limit") or 10000),
    }

    if viz == "big_number_total":
        metric = params.get("metric")
        spec["metric"] = metric
        spec["title"] = (metric or {}).get("label") or slice_name
        spec["value_format"] = _guess_format(metric)
        spec["section"] = "kpi"
    elif viz == "table":
        spec["columns"] = params.get("all_columns") or params.get("columns") or []
        spec["groupby"] = params.get("groupby") or []
        spec["metrics"] = params.get("metrics") or []
        spec["title"] = slice_name
        spec["section"] = "tables"
    elif viz in ("pie", "treemap_v2"):
        spec["metric"] = params.get("metric")
        spec["groupby"] = params.get("groupby") or []
        spec["title"] = slice_name
        spec["value_format"] = _guess_format(params.get("metric"))
        spec["section"] = "analytics"
    elif viz == "echarts_timeseries_bar":
        metrics = params.get("metrics") or []
        spec["metrics"] = metrics
        spec["metric"] = metrics[0] if metrics else params.get("metric")
        spec["dimension"] = params.get("x_axis") or (params.get("groupby") or [""])[0]
        spec["orientation"] = params.get("orientation") or "vertical"
        spec["value_format"] = _guess_format(spec["metric"])
        spec["title"] = slice_name
        spec["section"] = "analytics"
    else:
        spec["metric"] = params.get("metric") or (params.get("metrics") or [None])[0]
        spec["groupby"] = params.get("groupby") or []
        spec["columns"] = params.get("all_columns") or params.get("columns") or []
        spec["metrics"] = params.get("metrics") or []
        spec["title"] = slice_name
        spec["section"] = "analytics"
    return spec


# ---------------------------------------------------------------------------
# Session + login (token cached until JWT expiry, re-login on 401)
# ---------------------------------------------------------------------------
_session: requests.Session | None = None
_session_at: float = 0.0
_session_exp: float = 0.0
_session_lock = threading.Lock()
_TOKEN_TTL = 6 * 60 * 60


def _token_expiry(token: str) -> float:
    try:
        _, payload, _ = token.split(".")
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return float(claims.get("exp") or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _reset_session() -> None:
    global _session, _session_at, _session_exp
    with _session_lock:
        _session, _session_at, _session_exp = None, 0.0, 0.0


def _login() -> requests.Session:
    global _session, _session_at, _session_exp
    if _session is not None and time.time() - _session_at < _TOKEN_TTL and (_session_exp == 0.0 or time.time() < _session_exp):
        return _session
    with _session_lock:
        if _session is not None and time.time() - _session_at < _TOKEN_TTL and (_session_exp == 0.0 or time.time() < _session_exp):
            return _session
        base = superset_base_url()
        session = requests.Session()
        login = session.post(
            f"{base}/api/v1/security/login",
            json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
            timeout=_timeout(),
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        session.headers.update({"Authorization": f"Bearer {token}"})
        csrf = session.get(f"{base}/api/v1/security/csrf_token/", timeout=_timeout())
        csrf.raise_for_status()
        session.headers.update({"X-CSRFToken": csrf.json()["result"]})
        _session, _session_at, _session_exp = session, time.time(), _token_expiry(token)
        return session


def _api_call(method: str, url: str, **kwargs: Any) -> requests.Response:
    resp = getattr(_login(), method)(url, **kwargs)
    if resp.status_code == 401:
        _reset_session()
        resp = getattr(_login(), method)(url, **kwargs)
    return resp


def _api_get(url: str, **kwargs: Any) -> requests.Response:
    return _api_call("get", url, **kwargs)


def _api_post(url: str, **kwargs: Any) -> requests.Response:
    return _api_call("post", url, **kwargs)


# ---------------------------------------------------------------------------
# Dashboards + dynamic meta
# ---------------------------------------------------------------------------
_dashboard_cache: dict[str, dict[str, Any]] = {}
_DASHBOARD_TTL = 6 * 60 * 60


def _dashboard_cache_get(dashboard_id: int) -> dict[str, Any] | None:
    item = _dashboard_cache.get(str(dashboard_id))
    if item and time.time() - item["at"] < _DASHBOARD_TTL:
        return item["payload"]
    return None


def _dashboard_cache_set(dashboard_id: int, payload: dict[str, Any]) -> None:
    _dashboard_cache[str(dashboard_id)] = {"at": time.time(), "payload": payload}


def _fetch_dashboard_charts(dashboard_id: int) -> list[dict[str, Any]]:
    base = superset_base_url()
    detail = _api_get(f"{base}/api/v1/dashboard/{dashboard_id}", timeout=_timeout())
    detail.raise_for_status()
    result = detail.json()["result"]
    position = json.loads(result.get("position_json") or "{}")
    chart_comps = []
    for key, comp in position.items():
        if isinstance(comp, dict) and comp.get("type") == "CHART":
            meta = comp.get("meta") or {}
            if meta.get("chartId"):
                try:
                    order = int(key.split("-")[-1]) if "-" in key else len(chart_comps)
                except ValueError:
                    order = len(chart_comps)
                chart_comps.append((order, int(meta["chartId"])))
    chart_comps.sort(key=lambda t: t[0])
    ordered_ids = [cid for _, cid in chart_comps]
    specs = []
    for cid in ordered_ids:
        c = _api_get(f"{base}/api/v1/chart/{cid}", timeout=_timeout())
        c.raise_for_status()
        specs.append(_spec_from_chart(c.json()["result"]))
    return specs


def fetch_dashboards() -> list[dict[str, Any]]:
    base = superset_base_url()
    resp = _api_get(f"{base}/api/v1/dashboard/", timeout=_timeout())
    resp.raise_for_status()
    return [
        {"id": d.get("id"), "title": d.get("dashboard_title"), "url": d.get("url")}
        for d in resp.json().get("result", [])
        if d.get("id") is not None
    ]


def fetch_dashboard_meta(dashboard_id: int) -> dict[str, Any]:
    cached = _dashboard_cache_get(dashboard_id)
    if cached:
        return json.loads(json.dumps(cached))
    specs = _fetch_dashboard_charts(dashboard_id)
    meta = {
        "dashboard_id": dashboard_id,
        "dashboard_title": f"Dashboard #{dashboard_id}",
        "source": "superset_api",
        "chart_count": len(specs),
        "year_options": ["Semua", "2023", "2024", "2025"],
        "charts": specs,
    }
    if specs:
        meta["dashboard_title"] = specs[0].get("slice_name") or meta["dashboard_title"]
        base = superset_base_url()
        try:
            detail = _api_get(f"{base}/api/v1/dashboard/{dashboard_id}", timeout=_timeout())
            if detail.ok:
                meta["dashboard_title"] = detail.json()["result"].get("dashboard_title") or meta["dashboard_title"]
        except Exception:  # noqa: BLE001
            pass
    _dashboard_cache_set(dashboard_id, meta)
    return json.loads(json.dumps(meta))


def resolve_chart_spec(chart_id: int, dashboard_id: int | None = None) -> dict[str, Any] | None:
    if dashboard_id is not None:
        meta = _dashboard_cache_get(dashboard_id)
        if meta:
            for spec in meta["charts"]:
                if spec["id"] == int(chart_id):
                    return json.loads(json.dumps(spec))
    base = superset_base_url()
    try:
        c = _api_get(f"{base}/api/v1/chart/{chart_id}", timeout=_timeout())
        if not c.ok:
            return None
        return _spec_from_chart(c.json()["result"])
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Query building (mirrors Superset's stored query for the chart)
# ---------------------------------------------------------------------------
def _year_filter(year: str) -> dict[str, Any]:
    return {"col": "tahun", "op": "IN", "val": [str(year)]}


_FILTER_COLUMN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_CROSS_FILTERS = 12
_MAX_VALUES_PER_FILTER = 25
_FACT_FILTER_COLUMNS = frozenset(
    {
        "tahun",
        "prodi",
        "fakultas",
        "iku",
        "kode_iku",
        "kegiatan",
        "cluster_kegiatan",
        "akun",
        "kode_akun",
        "nama_akun",
        "uraian_detail",
        "source_file",
        "source_sheet",
        "source_role",
        "row_type",
        "status",
    }
)
_RECONCILIATION_FILTER_COLUMNS = frozenset({"tahun", "source_file", "status", "validation_type"})


def normalize_query_filters(filters: object) -> list[dict[str, Any]]:
    if filters is None:
        return []
    if not isinstance(filters, list):
        raise ValueError("filters harus berupa array JSON.")
    if len(filters) > _MAX_CROSS_FILTERS:
        raise ValueError(f"filters maksimal {_MAX_CROSS_FILTERS} kolom.")

    normalized: list[dict[str, Any]] = []
    seen_columns: set[str] = set()
    for item in filters:
        if not isinstance(item, dict):
            raise ValueError("Setiap filter harus berupa objek.")
        column = str(item.get("col") or "").strip()
        if not _FILTER_COLUMN_RE.fullmatch(column):
            raise ValueError("Nama kolom filter tidak valid.")
        if column in seen_columns:
            raise ValueError(f"Filter kolom duplikat: {column}.")
        operation = str(item.get("op") or "IN").upper().strip()
        if operation != "IN":
            raise ValueError("Operasi filter yang didukung hanya IN.")
        values = item.get("val")
        if not isinstance(values, list):
            values = [values]
        if not values or len(values) > _MAX_VALUES_PER_FILTER:
            raise ValueError(f"Filter {column} harus memiliki 1-{_MAX_VALUES_PER_FILTER} nilai.")
        clean_values: list[str | int | float | bool] = []
        for value in values:
            if value is None or isinstance(value, (dict, list, tuple)):
                raise ValueError(f"Nilai filter {column} tidak valid.")
            if isinstance(value, float) and not (value == value and abs(value) != float("inf")):
                raise ValueError(f"Nilai filter {column} tidak valid.")
            clean_value = str(value).strip() if isinstance(value, str) else value
            if clean_value == "":
                raise ValueError(f"Nilai filter {column} tidak boleh kosong.")
            if clean_value not in clean_values:
                clean_values.append(clean_value)
        seen_columns.add(column)
        normalized.append({"col": column, "op": "IN", "val": clean_values})
    return normalized


def parse_filter_query(raw_filters: str | None) -> list[dict[str, Any]]:
    if not raw_filters:
        return []
    try:
        payload = json.loads(raw_filters)
    except json.JSONDecodeError as exc:
        raise ValueError("filters bukan JSON yang valid.") from exc
    return normalize_query_filters(payload)


def _filter_columns_for_spec(spec: dict[str, Any]) -> frozenset[str]:
    title = str(spec.get("title") or spec.get("slice_name") or "").lower()
    if "rekonsiliasi" in title or "validasi" in title:
        return _RECONCILIATION_FILTER_COLUMNS
    return _FACT_FILTER_COLUMNS


def _filters_supported_by_spec(spec: dict[str, Any], filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    supported = _filter_columns_for_spec(spec)
    return [item for item in filters if item["col"] in supported]


def _query_context(spec: dict[str, Any], year: str | None, cross_filters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    filters = [_year_filter(year)] if year else []
    filters.extend(normalize_query_filters(cross_filters))
    viz = spec["viz_type"]
    metrics = list(spec.get("metrics") or ([] if viz == "table" else []))
    if not metrics and spec.get("metric"):
        metrics = [spec["metric"]]
    if viz == "big_number_total":
        columns, groupby = [], []
    elif viz == "table":
        columns = list(spec.get("columns") or [])
        groupby = list(spec.get("groupby") or [])
        if not columns and groupby:
            columns = list(groupby)
    else:
        groupby = list(spec.get("groupby") or ([spec["dimension"]] if spec.get("dimension") else []))
        columns = list(groupby)
    return {
        "columns": columns,
        "metrics": metrics,
        "filters": filters,
        "groupby": groupby,
        "extras": {"having": "", "where": ""},
        "applied_time_extras": {},
        "annotation_layers": [],
        "row_limit": int(spec.get("row_limit", 10000)),
        "series_limit": 0,
    }


def _form_data(spec: dict[str, Any], year: str | None, cross_filters: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    viz = spec["viz_type"]
    fd: dict[str, Any] = {
        "datasource": f"{spec['datasource']['id']}__{spec['datasource']['type']}",
        "viz_type": viz,
        "row_limit": int(spec.get("row_limit", 10000)),
        "time_range": "No filter",
        "adhoc_filters": [],
    }
    if year:
        fd["adhoc_filters"].append(
            {"clause": "WHERE", "expressionType": "SIMPLE", "operator": "IN", "subject": "tahun", "comparator": [str(year)]}
        )
    for cross_filter in normalize_query_filters(cross_filters):
        fd["adhoc_filters"].append(
            {
                "clause": "WHERE",
                "expressionType": "SIMPLE",
                "operator": "IN",
                "subject": cross_filter["col"],
                "comparator": cross_filter["val"],
            }
        )
    if viz == "big_number_total":
        fd["metric"] = spec["metric"]
    elif viz in ("pie", "treemap_v2"):
        fd["metric"] = spec.get("metric")
        fd["groupby"] = list(spec.get("groupby") or [])
    elif viz == "echarts_timeseries_bar":
        fd["metrics"] = list(spec.get("metrics") or ([spec["metric"]] if spec.get("metric") else []))
        fd["x_axis"] = spec.get("dimension")
        fd["orientation"] = spec.get("orientation") or "vertical"
        fd["y_axis_format"] = ",d"
    else:
        fd["columns"] = list(spec.get("columns") or spec.get("groupby") or [])
        metrics = spec.get("metrics")
        if metrics:
            fd["metrics"] = list(metrics)
    return fd


# ---------------------------------------------------------------------------
# Chart data fetching (direct from Superset REST API, no database reads)
# ---------------------------------------------------------------------------
_cache: dict[str, dict[str, Any]] = {}
_CACHE_TTL = 60.0


def _cache_key(chart_id: int, year: str | None, cross_filters: list[dict[str, Any]] | None = None) -> str:
    filter_key = json.dumps(normalize_query_filters(cross_filters), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"{chart_id}:{year or 'all'}:{filter_key}"


def _read_cache(chart_id: int, year: str | None, cross_filters: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    item = _cache.get(_cache_key(chart_id, year, cross_filters))
    if item and time.time() - item["at"] < _CACHE_TTL:
        return item["payload"]
    return None


def _write_cache(chart_id: int, year: str | None, payload: dict[str, Any], cross_filters: list[dict[str, Any]] | None = None) -> None:
    _cache[_cache_key(chart_id, year, cross_filters)] = {"at": time.time(), "payload": payload}
    if len(_cache) > 300:
        oldest = min(_cache, key=lambda k: _cache[k]["at"])
        _cache.pop(oldest, None)


def _extract(result: dict[str, Any]) -> dict[str, Any]:
    first = (result.get("result") or [{}])[0] if result.get("result") else {}
    return {
        "status": first.get("status") or "error",
        "error": first.get("error"),
        "data": first.get("data") or [],
        "colnames": first.get("colnames") or [],
        "rowcount": first.get("rowcount"),
        "sql_rowcount": first.get("sql_rowcount"),
        "query": first.get("query"),
        "from_dttm": first.get("from_dttm"),
        "to_dttm": first.get("to_dttm"),
    }


def fetch_chart_data(
    chart_id: int,
    year: str | None = None,
    dashboard_id: int | None = None,
    refresh: bool = False,
    cross_filters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    spec = resolve_chart_spec(chart_id, dashboard_id)
    if spec is None:
        return {"status": "error", "error": f"chart_id {chart_id} tidak dikenal di Superset"}
    try:
        normalized_filters = normalize_query_filters(cross_filters)
    except ValueError as exc:
        return {"status": "error", "error": str(exc), "chart_id": int(chart_id), "year": year}
    supported_filters = _filters_supported_by_spec(spec, normalized_filters)
    if not refresh:
        cached = _read_cache(int(chart_id), year, normalized_filters)
        if cached:
            return cached
    base = superset_base_url()
    try:
        body = {
            "datasource": {"id": spec["datasource"]["id"], "type": spec["datasource"]["type"]},
            "force": True,
            "queries": [_query_context(spec, year, supported_filters)],
            "form_data": _form_data(spec, year, supported_filters),
            "result_format": "json",
            "result_type": "full",
        }
        response = _api_post(f"{base}/api/v1/chart/data", json=body, timeout=_timeout())
        response.raise_for_status()
        payload = _extract(response.json())
        payload["chart_id"] = int(chart_id)
        payload["year"] = year
        payload["filters"] = normalized_filters
        payload["source"] = "superset_api"
        if refresh:
            # refresh replaces cache entry so the UI shows the newest Superset data
            _cache[_cache_key(int(chart_id), year, normalized_filters)] = {"at": time.time(), "payload": payload}
        else:
            _write_cache(int(chart_id), year, payload, normalized_filters)
        return payload
    except Exception as exc:  # noqa: BLE001 - surface any upstream error to the UI
        return {"status": "unreachable", "error": str(exc), "chart_id": int(chart_id), "year": year, "source": "superset_api"}
