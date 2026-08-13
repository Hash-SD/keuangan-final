from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.common.logging_utils import write_json
from src.common.time_utils import utc_now_iso
from src.gold.contract import DASHBOARD_FILTERS, FACT_COLUMNS

from .paths import OUTPUTS_DIR, ROOT_DIR
from .superset_api import fetch_superset_fact_rows, read_superset_reference


DASHBOARD_VIEW_RELATIVE = "data/generated/gold/fact_anggaran.csv"
DASHBOARD_VIEW_PATH = ROOT_DIR / DASHBOARD_VIEW_RELATIVE
SUPERSET_GOLD_RELATIVE = DASHBOARD_VIEW_RELATIVE
SUPERSET_GOLD_PATH = ROOT_DIR / SUPERSET_GOLD_RELATIVE
NOT_AVAILABLE_MESSAGE = "Gold fact anggaran belum tersedia. Jalankan pipeline sampai Gold terlebih dahulu."

FILTER_COLUMNS = list(DASHBOARD_FILTERS)
SUPERSET_REQUIRED_COLUMNS = [
    "dataset_session_id",
    "run_id",
    "item_id",
    "tahun",
    "prodi",
    "iku",
    "kegiatan",
    "akun",
    "jumlah_weighted_iku",
]

SUPERSET_LABELS = {
    "title": "Dashboard Anggaran RAB/IKU",
    "subtitle": "Laporan tahunan dari Gold fact_anggaran pada grain item anggaran dan alokasi IKU.",
    "value_label": "Total Anggaran",
    "item_label": "Jumlah Item",
    "iku_label": "Jumlah IKU",
    "activity_label": "Jumlah Kegiatan",
    "status_label": "Status Rekonsiliasi",
    "table_title": "Detail Item Biaya",
}

OPTIONAL_ANALYTIC_COLUMNS = {
    "prodi": "-",
    "fakultas": "-",
    "iku": "-",
    "kode_iku": "-",
    "kegiatan": "-",
    "akun": "-",
    "uraian_detail": "-",
    "source_file": "-",
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT_DIR.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _empty_response(status: str = "not_available", message: str = NOT_AVAILABLE_MESSAGE) -> dict[str, Any]:
    return {
        "status": status,
        "source": None,
        "source_kind": None,
        "source_dataset": "fact_anggaran",
        "generated_at": utc_now_iso(),
        "message": message,
        "data": None,
    }


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [{key: _clean_value(value) for key, value in row.items()} for row in frame.to_dict(orient="records")]


def _ensure_analytic_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column, fallback in OPTIONAL_ANALYTIC_COLUMNS.items():
        values = normalized[column] if column in normalized.columns else pd.Series(fallback, index=normalized.index)
        normalized[column] = values.fillna(fallback).astype(str)
    for column in ("jumlah", "jumlah_weighted_iku", "qty", "harga_satuan", "allocation_weight"):
        if column in normalized.columns:
            normalized[column] = pd.to_numeric(normalized[column], errors="coerce").fillna(0)
    return normalized


def _query_filters(args: Any | None) -> dict[str, list[str]]:
    if args is None:
        return {}
    filters: dict[str, list[str]] = {}
    for column in FILTER_COLUMNS:
        values = args.getlist(column) if hasattr(args, "getlist") else []
        if isinstance(args, dict):
            raw = args.get(column)
            values = raw if isinstance(raw, list) else ([raw] if raw not in {None, ""} else [])
        split_values = [part.strip() for value in values for part in str(value).split(",") if part.strip()]
        if split_values:
            filters[column] = split_values
    return filters


def _metadata(source: str, source_kind: str, row_count: int, source_note: str | None = None) -> dict[str, Any]:
    payload = {
        "status": "gold_csv_ready" if source_kind == "gold_fact_anggaran" else "superset_api_ready",
        "source": source,
        "source_kind": source_kind,
        "source_dataset": "fact_anggaran",
        "labels": SUPERSET_LABELS,
        "generated_at": utc_now_iso(),
        "row_count": int(row_count),
    }
    if source_note:
        payload["source_note"] = source_note
    return payload


def _load_superset_api_view() -> tuple[pd.DataFrame | None, dict[str, Any]]:
    source, api_metadata = fetch_superset_fact_rows()
    if source is None or source.empty:
        return None, api_metadata
    missing = [column for column in SUPERSET_REQUIRED_COLUMNS if column not in source.columns]
    if missing:
        return None, {
            "status": "missing_columns",
            "source": "superset_api:/api/v1/chart/data",
            "source_kind": "superset_api",
            "source_dataset": "fact_anggaran",
            "generated_at": utc_now_iso(),
            "message": "Superset API fact_anggaran belum memiliki kolom dashboard yang wajib.",
            "missing_columns": missing,
            "superset_reference": api_metadata.get("superset_reference"),
            "data": None,
        }
    frame = _ensure_analytic_columns(source)
    metadata = _metadata(
        "superset_api:/api/v1/chart/data",
        "superset_api",
        len(frame),
        "Dashboard lokal membaca dataset fact_anggaran melalui Superset API.",
    )
    return frame, {
        **metadata,
        "source_priority": ["superset_api", "gold_fact_anggaran"],
        "superset_reference": api_metadata.get("superset_reference"),
    }


def _load_superset_gold_view() -> tuple[pd.DataFrame | None, dict[str, Any]]:
    try:
        source = pd.read_csv(SUPERSET_GOLD_PATH, low_memory=False)
    except Exception as exc:
        return None, _empty_response("failed", f"Gold fact_anggaran gagal dibaca: {exc}")
    missing = [column for column in SUPERSET_REQUIRED_COLUMNS if column not in source.columns]
    if missing:
        return None, {
            "status": "missing_columns",
            "source": _rel(SUPERSET_GOLD_PATH),
            "source_kind": "gold_fact_anggaran",
            "source_dataset": "fact_anggaran",
            "generated_at": utc_now_iso(),
            "message": "Gold fact_anggaran belum memiliki kolom dashboard yang wajib.",
            "missing_columns": missing,
            "data": None,
        }
    frame = _ensure_analytic_columns(source)
    return frame, {
        **_metadata(
            _rel(SUPERSET_GOLD_PATH),
            "gold_fact_anggaran",
            len(frame),
            "Fallback lokal membaca Gold fact_anggaran yang sama dengan dataset Superset.",
        ),
        "source_priority": ["superset_api", "gold_fact_anggaran"],
        "superset_reference": read_superset_reference(),
        "fallback_reason": "superset_api_unavailable",
    }


def load_dashboard_view(path: Path | None = None) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    source_path = path or DASHBOARD_VIEW_PATH
    if not source_path.exists() and path is None:
        superset_frame, superset_metadata = _load_superset_api_view()
        if superset_frame is not None:
            return superset_frame, superset_metadata
        if SUPERSET_GOLD_PATH.exists():
            return _load_superset_gold_view()
    if not source_path.exists():
        return None, _empty_response()
    try:
        frame = pd.read_csv(source_path, low_memory=False)
    except Exception as exc:
        return None, _empty_response("failed", f"Gold fact_anggaran gagal dibaca: {exc}")
    return _ensure_analytic_columns(frame), _metadata(_rel(source_path), "gold_fact_anggaran", len(frame))


def validate_dashboard_columns(frame: pd.DataFrame | None) -> dict[str, Any]:
    if frame is None:
        return {"status": "gold_csv_missing", "missing_columns": SUPERSET_REQUIRED_COLUMNS}
    missing = [column for column in SUPERSET_REQUIRED_COLUMNS if column not in frame.columns]
    forbidden = [column for column in ("periode", "pipeline_run_id") if column in frame.columns]
    if missing:
        return {"status": "missing_columns", "missing_columns": missing}
    if forbidden:
        return {"status": "forbidden_columns", "missing_columns": [], "forbidden_columns": forbidden}
    return {"status": "validated", "missing_columns": [], "forbidden_columns": []}


def apply_dashboard_filters(frame: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    filtered = frame
    for column, values in filters.items():
        if column not in FILTER_COLUMNS or not values:
            continue
        if column not in filtered.columns:
            return filtered.iloc[0:0].copy()
        filtered = filtered[filtered[column].astype(str).isin({str(value) for value in values})]
    return filtered.copy()


def build_available_filters(frame: pd.DataFrame) -> dict[str, list[str]]:
    return {
        column: sorted(
            [value for value in frame[column].dropna().astype(str).unique().tolist() if value and value != "-"],
            key=lambda value: (value.lower(), value),
        )
        if column in frame.columns
        else []
        for column in FILTER_COLUMNS
    }


def _unique_count(frame: pd.DataFrame, column: str) -> int:
    if column not in frame.columns:
        return 0
    values = frame[column].dropna().astype(str).replace({"": pd.NA, "-": pd.NA})
    return int(values.dropna().nunique())


def _reconciliation_status(frame: pd.DataFrame) -> str:
    if "status" in frame.columns:
        values = {str(value).upper() for value in frame["status"].dropna()}
        return "OK" if values and values == {"OK"} else ("CHECK" if values else "NOT_AVAILABLE")
    if frame.empty:
        return "NOT_AVAILABLE"
    identity = [column for column in ("dataset_session_id", "run_id", "item_id") if column in frame.columns]
    item_level = frame.drop_duplicates(identity) if identity else frame
    raw_total = pd.to_numeric(item_level.get("jumlah"), errors="coerce").fillna(0).sum()
    weighted_total = pd.to_numeric(frame.get("jumlah_weighted_iku"), errors="coerce").fillna(0).sum()
    return "OK" if abs(float(raw_total) - float(weighted_total)) <= 0.01 else "CHECK"


def build_summary(frame: pd.DataFrame) -> dict[str, Any]:
    weighted = pd.to_numeric(frame.get("jumlah_weighted_iku"), errors="coerce").fillna(0)
    return {
        "total_anggaran": float(weighted.sum()),
        "jumlah_item": _unique_count(frame, "item_id"),
        "jumlah_iku": _unique_count(frame, "kode_iku" if "kode_iku" in frame.columns else "iku"),
        "jumlah_kegiatan": _unique_count(frame, "kegiatan"),
        "status_rekonsiliasi": _reconciliation_status(frame),
        "row_count": int(len(frame)),
        "prodi_count": _unique_count(frame, "prodi"),
    }


def _series(frame: pd.DataFrame, dimension: str, limit: int | None = None) -> list[dict[str, Any]]:
    if frame.empty or dimension not in frame.columns:
        return []
    grouped = (
        frame.assign(_amount=pd.to_numeric(frame["jumlah_weighted_iku"], errors="coerce").fillna(0))
        .groupby(dimension, dropna=False)
        .agg(total_anggaran=("_amount", "sum"), jumlah_item=("item_id", "nunique"))
        .reset_index()
        .rename(columns={dimension: "label"})
    )
    grouped["label"] = grouped["label"].fillna("-").astype(str)
    if dimension == "tahun":
        grouped = grouped.sort_values("label", ascending=True)
    else:
        grouped = grouped.sort_values(["total_anggaran", "label"], ascending=[False, True])
    return _records(grouped.head(limit) if limit is not None else grouped)


def build_chart_payloads(frame: pd.DataFrame) -> dict[str, Any]:
    return {
        "ringkasan_per_tahun": {"filter_column": "tahun", "items": _series(frame, "tahun")},
        "anggaran_per_tahun": {"filter_column": "tahun", "items": _series(frame, "tahun")},
        "anggaran_per_iku": {"filter_column": "iku", "items": _series(frame, "iku")},
        "cluster_kegiatan": {"filter_column": "kegiatan", "items": _series(frame, "kegiatan", limit=20)},
        "komposisi_akun": {"filter_column": "akun", "items": _series(frame, "akun", limit=25)},
        "anggaran_per_akun": {"filter_column": "akun", "items": _series(frame, "akun")},
        "validasi_rekap": {"status": _reconciliation_status(frame)},
    }


def build_detail_table(frame: pd.DataFrame, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    columns = [
        "tahun",
        "prodi",
        "iku",
        "kegiatan",
        "akun",
        "uraian_detail",
        "qty",
        "satuan",
        "harga_satuan",
        "jumlah",
        "allocation_weight",
        "jumlah_weighted_iku",
        "source_file",
        "item_id",
    ]
    available = [column for column in columns if column in frame.columns]
    ordered = frame.assign(_amount=pd.to_numeric(frame.get("jumlah_weighted_iku"), errors="coerce").fillna(0)).sort_values("_amount", ascending=False)
    start = max(offset, 0)
    page = ordered[available].iloc[start : start + max(limit, 1)]
    return {"columns": columns, "rows": _records(page), "total_rows": int(len(frame)), "limit": int(limit), "offset": int(offset)}


def build_dashboard_response(args: Any | None = None, section: str = "all", path: Path | None = None) -> dict[str, Any]:
    frame, metadata = load_dashboard_view(path)
    validation = validate_dashboard_columns(frame)
    if frame is None:
        return metadata
    if validation["status"] != "validated":
        return {
            "status": validation["status"],
            "source": metadata.get("source"),
            "generated_at": metadata.get("generated_at"),
            "message": "Gold fact_anggaran belum memenuhi kontrak dashboard.",
            "missing_columns": validation.get("missing_columns", []),
            "forbidden_columns": validation.get("forbidden_columns", []),
            "data": None,
        }

    filters = _query_filters(args)
    filtered = apply_dashboard_filters(frame, filters)
    response: dict[str, Any] = {
        "status": "empty_after_filter" if filtered.empty else "validated",
        "source": metadata.get("source"),
        "source_kind": metadata.get("source_kind"),
        "source_dataset": metadata.get("source_dataset"),
        "source_note": metadata.get("source_note"),
        "source_priority": metadata.get("source_priority"),
        "superset_reference": metadata.get("superset_reference"),
        "generated_at": metadata.get("generated_at"),
        "filters": filters,
        "data": {"labels": metadata.get("labels", SUPERSET_LABELS)},
    }
    if section in {"all", "status"}:
        response["data"]["status"] = {"row_count": int(len(frame)), "filtered_row_count": int(len(filtered))}
    if section in {"all", "filters"}:
        response["data"]["filters"] = build_available_filters(frame)
    if section in {"all", "summary"}:
        response["data"]["summary"] = build_summary(filtered)
    if section in {"all", "charts"}:
        response["data"]["charts"] = build_chart_payloads(filtered)
    if section in {"all", "table"}:
        limit = args.get("limit", 50, type=int) if hasattr(args, "get") else 50
        offset = args.get("offset", 0, type=int) if hasattr(args, "get") else 0
        response["data"]["table"] = build_detail_table(filtered, limit=limit, offset=offset)
    return response


def dashboard_section(args: Any | None, section: str) -> dict[str, Any]:
    payload = build_dashboard_response(args=args, section=section)
    if payload.get("data") is None or section == "all":
        return payload
    data = payload.get("data", {})
    payload["data"] = data.get(section)
    return payload


def write_dashboard_reports() -> dict[str, Any]:
    status_payload = dashboard_section(None, "status")
    all_payload = build_dashboard_response(section="all")
    validation_payload = {
        "status": all_payload.get("status"),
        "source": all_payload.get("source"),
        "source_kind": all_payload.get("source_kind"),
        "source_dataset": all_payload.get("source_dataset"),
        "generated_at": all_payload.get("generated_at"),
        "message": all_payload.get("message"),
        "filters": all_payload.get("data", {}).get("filters") if isinstance(all_payload.get("data"), dict) else None,
    }
    reports = OUTPUTS_DIR / "reports"
    write_json(reports / "local_dashboard_api_status.json", status_payload)
    write_json(reports / "local_dashboard_validation.json", validation_payload)
    write_json(reports / "local_dashboard_sample_response.json", all_payload)
    return all_payload
