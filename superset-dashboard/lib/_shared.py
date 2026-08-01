from __future__ import annotations

import json
import os
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
# Session + login (token cached 6h)
# ---------------------------------------------------------------------------
_session: requests.Session | None = None
_session_at: float = 0.0
_TOKEN_TTL = 6 * 60 * 60


def _login() -> requests.Session:
    global _session, _session_at
    if _session is not None and time.time() - _session_at < _TOKEN_TTL:
        return _session
    base = superset_base_url()
    session = requests.Session()
    login = session.post(
        f"{base}/api/v1/security/login",
        json={"username": USERNAME, "password": PASSWORD, "provider": "db", "refresh": True},
        timeout=_timeout(),
    )
    login.raise_for_status()
    session.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    csrf = session.get(f"{base}/api/v1/security/csrf_token/", timeout=_timeout())
    csrf.raise_for_status()
    session.headers.update({"X-CSRFToken": csrf.json()["result"]})
    _session, _session_at = session, time.time()
    return session


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
    session = _login()
    detail = session.get(f"{base}/api/v1/dashboard/{dashboard_id}", timeout=_timeout())
    detail.raise_for_status()
    result = detail.json()["result"]
    position = json.loads(result.get("position_json") or "{}")
    chart_comps = []
    for key, comp in position.items():
        if isinstance(comp, dict) and comp.get("type") == "CHART":
            meta = comp.get("meta") or {}
            if meta.get("chartId"):
                order = int(key.split("-")[-1]) if "-" in key else len(chart_comps)
                chart_comps.append((order, int(meta["chartId"])))
    chart_comps.sort(key=lambda t: t[0])
    ordered_ids = [cid for _, cid in chart_comps]
    specs = []
    for cid in ordered_ids:
        c = session.get(f"{base}/api/v1/chart/{cid}", timeout=_timeout())
        c.raise_for_status()
        specs.append(_spec_from_chart(c.json()["result"]))
    return specs


def fetch_dashboards() -> list[dict[str, Any]]:
    base = superset_base_url()
    session = _login()
    resp = session.get(f"{base}/api/v1/dashboard/", timeout=_timeout())
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
        meta["dashboard_title"] = specs[0].get("slice_name") and f"Dashboard #{dashboard_id}" or meta["dashboard_title"]
        base = superset_base_url()
        try:
            session = _login()
            detail = session.get(f"{base}/api/v1/dashboard/{dashboard_id}", timeout=_timeout())
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
        session = _login()
        c = session.get(f"{base}/api/v1/chart/{chart_id}", timeout=_timeout())
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


def _query_context(spec: dict[str, Any], year: str | None) -> dict[str, Any]:
    filters = [_year_filter(year)] if year else []
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


def _form_data(spec: dict[str, Any], year: str | None) -> dict[str, Any]:
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


def _cache_key(chart_id: int, year: str | None) -> str:
    return f"{chart_id}:{year or 'all'}"


def _read_cache(chart_id: int, year: str | None) -> dict[str, Any] | None:
    item = _cache.get(_cache_key(chart_id, year))
    if item and time.time() - item["at"] < _CACHE_TTL:
        return item["payload"]
    return None


def _write_cache(chart_id: int, year: str | None, payload: dict[str, Any]) -> None:
    _cache[_cache_key(chart_id, year)] = {"at": time.time(), "payload": payload}
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


def fetch_chart_data(chart_id: int, year: str | None = None, dashboard_id: int | None = None, refresh: bool = False) -> dict[str, Any]:
    spec = resolve_chart_spec(chart_id, dashboard_id)
    if spec is None:
        return {"status": "error", "error": f"chart_id {chart_id} tidak dikenal di Superset"}
    if not refresh:
        cached = _read_cache(int(chart_id), year)
        if cached:
            return cached
    base = superset_base_url()
    try:
        session = _login()
        body = {
            "datasource": {"id": spec["datasource"]["id"], "type": spec["datasource"]["type"]},
            "force": True,
            "queries": [_query_context(spec, year)],
            "form_data": _form_data(spec, year),
            "result_format": "json",
            "result_type": "full",
        }
        response = session.post(f"{base}/api/v1/chart/data", json=body, timeout=_timeout())
        response.raise_for_status()
        payload = _extract(response.json())
        payload["chart_id"] = int(chart_id)
        payload["year"] = year
        payload["source"] = "superset_api"
        if refresh:
            # refresh replaces cache entry so the UI shows the newest Superset data
            _cache[_cache_key(int(chart_id), year)] = {"at": time.time(), "payload": payload}
        else:
            _write_cache(int(chart_id), year, payload)
        return payload
    except Exception as exc:  # noqa: BLE001 - surface any upstream error to the UI
        return {"status": "unreachable", "error": str(exc), "chart_id": int(chart_id), "year": year, "source": "superset_api"}
