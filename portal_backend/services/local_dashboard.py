from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.common.logging_utils import write_json
from src.common.time_utils import utc_now_iso

from .paths import OUTPUTS_DIR, ROOT_DIR
from .superset_api import fetch_superset_fact_rows, read_superset_reference


DASHBOARD_VIEW_RELATIVE = "data/generated/gold/vw_dashboard_piutang_ukt.csv"
DASHBOARD_VIEW_PATH = ROOT_DIR / DASHBOARD_VIEW_RELATIVE
SUPERSET_GOLD_RELATIVE = "data/generated/gold/fact_anggaran.csv"
SUPERSET_GOLD_PATH = ROOT_DIR / SUPERSET_GOLD_RELATIVE
NOT_AVAILABLE_MESSAGE = "Gold dashboard view belum tersedia. Jalankan pipeline sampai Gold terlebih dahulu."

REQUIRED_COLUMNS = [
    "tahun_akademik",
    "tahun_anggaran",
    "semester",
    "nama_prodi",
    "nama_fakultas",
    "kualitas",
    "nominal_piutang_rp",
    "jumlah_mhs_penunggak",
    "nim",
    "nama_debitur",
]

FILTER_COLUMNS = [
    "item_id",
    "tahun_akademik",
    "tahun_anggaran",
    "semester",
    "nama_prodi",
    "kualitas",
    "iku",
    "kegiatan",
    "akun",
]

SUPERSET_REQUIRED_COLUMNS = [
    "tahun",
    "periode",
    "prodi",
    "fakultas",
    "item_id",
    "kegiatan",
    "jumlah",
]

PIUTANG_LABELS = {
    "title": "Dashboard Lokal Piutang UKT",
    "subtitle": "Data dibaca dari Gold view vw_dashboard_piutang_ukt.",
    "value_label": "Total Piutang",
    "count_label": "Mahasiswa Penunggak",
    "entity_label": "Debitur Unik",
    "row_label": "Baris Detail",
    "value_note": "nominal_piutang_rp dari Gold",
    "count_note": "jumlah_mhs_penunggak dari Gold",
    "entity_note": "distinct nim",
    "table_title": "Drill-down Detail Debitur",
    "name_column": "Debitur",
    "id_column": "NIM",
    "amount_column": "Nominal",
}

SUPERSET_LABELS = {
    "title": "Dashboard Anggaran IKU Sains Data",
    "subtitle": "Data dibaca dari Gold fact_anggaran, dataset yang sama dengan dashboard Superset.",
    "value_label": "Total Anggaran",
    "count_label": "Item Anggaran",
    "entity_label": "Item Unik",
    "row_label": "Baris Detail",
    "value_note": "jumlah_weighted_iku/jumlah dari Gold fact_anggaran",
    "count_note": "jumlah baris item dari dataset Superset",
    "entity_note": "distinct item_id",
    "table_title": "Drill-down Detail Item Biaya",
    "name_column": "Kegiatan",
    "id_column": "Item ID",
    "amount_column": "Nilai",
}

OPTIONAL_ANALYTIC_COLUMNS = {
    "iku": "-",
    "kegiatan": "-",
    "akun": "-",
    "mapping_status": "-",
    "uraian_detail": "-",
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
        "generated_at": utc_now_iso(),
        "message": message,
        "data": None,
    }


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows = frame.to_dict(orient="records")
    return [{key: _clean_value(value) for key, value in row.items()} for row in rows]


def _ensure_analytic_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for column, fallback in OPTIONAL_ANALYTIC_COLUMNS.items():
        if column not in normalized.columns:
            normalized[column] = fallback
        normalized[column] = normalized[column].fillna(fallback).astype(str)
    return normalized


def _query_filters(args: Any | None) -> dict[str, list[str]]:
    if args is None:
        return {}
    filters: dict[str, list[str]] = {}
    for column in FILTER_COLUMNS:
        values = []
        if hasattr(args, "getlist"):
            values = args.getlist(column)
        elif isinstance(args, dict):
            raw = args.get(column)
            if isinstance(raw, list):
                values = raw
            elif raw not in {None, ""}:
                values = [raw]
        split_values: list[str] = []
        for value in values:
            split_values.extend(part.strip() for part in str(value).split(",") if part.strip())
        if split_values:
            filters[column] = split_values
    return filters


def load_dashboard_view(path: Path | None = None) -> tuple[pd.DataFrame | None, dict[str, Any]]:
    source_path = path or DASHBOARD_VIEW_PATH
    source_kind = "piutang_ukt"
    labels = PIUTANG_LABELS
    if not source_path.exists() and path is None and _rel(source_path) == DASHBOARD_VIEW_RELATIVE:
        superset_frame, superset_metadata = _load_superset_api_view()
        if superset_frame is not None:
            return superset_frame, superset_metadata
    if not source_path.exists() and path is None and SUPERSET_GOLD_PATH.exists():
        return _load_superset_gold_view()
    if not source_path.exists():
        return None, _empty_response("not_available")
    try:
        frame = pd.read_csv(source_path, low_memory=False)
    except Exception as exc:
        return None, _empty_response("failed", f"Gold dashboard view gagal dibaca: {exc}")
    metadata = {
        "status": "gold_csv_ready",
        "source": _rel(source_path),
        "source_kind": source_kind,
        "source_dataset": "vw_dashboard_piutang_ukt",
        "labels": labels,
        "generated_at": utc_now_iso(),
        "row_count": int(len(frame)),
    }
    return frame, metadata


def _fact_to_dashboard_frame(source: pd.DataFrame) -> pd.DataFrame:
    amount_column = "jumlah_weighted_iku" if "jumlah_weighted_iku" in source.columns else "jumlah"
    return pd.DataFrame(
        {
            "tahun_akademik": source["tahun"].astype(str),
            "tahun_anggaran": source["tahun"].astype(str),
            "semester": source["periode"].fillna("Tahunan").astype(str),
            "nama_prodi": source["prodi"].fillna("-").astype(str),
            "nama_fakultas": source["fakultas"].fillna("-").astype(str),
            "kualitas": source.get("data_quality_flag", source.get("mapping_status", pd.Series(["-"] * len(source)))).fillna("-").astype(str),
            "nominal_piutang_rp": pd.to_numeric(source[amount_column], errors="coerce").fillna(0),
            "jumlah_mhs_penunggak": 1,
            "nim": source["item_id"].fillna("-").astype(str),
            "nama_debitur": source["kegiatan"].fillna(source.get("uraian_detail", "-")).astype(str),
            "iku": source.get("iku", source.get("kode_iku", pd.Series(["-"] * len(source)))).fillna("-").astype(str),
            "kegiatan": source["kegiatan"].fillna("-").astype(str),
            "akun": source.get("akun", source.get("nama_akun", pd.Series(["-"] * len(source)))).fillna("-").astype(str),
            "mapping_status": source.get("mapping_status", source.get("data_quality_flag", pd.Series(["-"] * len(source)))).fillna("-").astype(str),
            "uraian_detail": source.get("uraian_detail", source["kegiatan"]).fillna("-").astype(str),
        }
    )


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
            "message": "Superset API fact_anggaran tidak memiliki kolom minimum untuk dashboard lokal.",
            "missing_columns": missing,
            "superset_reference": api_metadata.get("superset_reference"),
            "data": None,
        }
    frame = _fact_to_dashboard_frame(source)
    metadata = {
        "status": "superset_api_ready",
        "source": "superset_api:/api/v1/chart/data",
        "source_kind": "superset_api",
        "source_dataset": "fact_anggaran",
        "source_priority": ["superset_api", "gold_fact_anggaran"],
        "source_note": "Data dashboard lokal dibaca melalui Superset API chart/data dari dataset fact_anggaran.",
        "superset_reference": api_metadata.get("superset_reference"),
        "labels": SUPERSET_LABELS,
        "generated_at": utc_now_iso(),
        "row_count": int(len(frame)),
    }
    return frame, metadata


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
            "message": "Gold fact_anggaran tidak memiliki kolom minimum untuk dashboard lokal.",
            "missing_columns": missing,
            "data": None,
        }
    frame = _fact_to_dashboard_frame(source)
    metadata = {
        "status": "gold_csv_ready",
        "source": _rel(SUPERSET_GOLD_PATH),
        "source_kind": "gold_fact_anggaran",
        "source_dataset": "fact_anggaran",
        "source_priority": ["superset_api", "gold_fact_anggaran"],
        "superset_reference": read_superset_reference(),
        "source_note": "Fallback faktual: Superset API belum tersedia, sehingga dashboard lokal membaca Gold fact_anggaran yang sama dengan dataset Superset.",
        "labels": SUPERSET_LABELS,
        "generated_at": utc_now_iso(),
        "row_count": int(len(frame)),
        "fallback_reason": "superset_api_unavailable",
    }
    return frame, metadata


def validate_dashboard_columns(frame: pd.DataFrame | None) -> dict[str, Any]:
    if frame is None:
        return {"status": "gold_csv_missing", "missing_columns": REQUIRED_COLUMNS}
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        return {"status": "missing_columns", "missing_columns": missing}
    return {"status": "validated", "missing_columns": []}


def apply_dashboard_filters(frame: pd.DataFrame, filters: dict[str, list[str]]) -> pd.DataFrame:
    filtered = frame
    for column, values in filters.items():
        if column not in FILTER_COLUMNS or not values:
            continue
        if column not in filtered.columns:
            return filtered.iloc[0:0].copy()
        allowed = {str(value) for value in values}
        filtered = filtered[filtered[column].astype(str).isin(allowed)]
    return filtered.copy()


def build_available_filters(frame: pd.DataFrame) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for column in FILTER_COLUMNS:
        if column not in frame.columns:
            result[column] = []
            continue
        values = frame[column].dropna().astype(str).unique().tolist()
        result[column] = sorted([value for value in values if value and value != "-"], key=lambda value: (value.lower(), value))
    return result


def build_summary(frame: pd.DataFrame) -> dict[str, Any]:
    nominal = pd.to_numeric(frame["nominal_piutang_rp"], errors="coerce").fillna(0)
    penunggak = pd.to_numeric(frame["jumlah_mhs_penunggak"], errors="coerce").fillna(0)
    return {
        "total_nominal_piutang_rp": float(nominal.sum()),
        "total_jumlah_mhs_penunggak": int(penunggak.sum()),
        "total_debitur_unik": int(frame["nim"].dropna().astype(str).nunique()),
        "row_count": int(len(frame)),
        "prodi_count": int(frame["nama_prodi"].dropna().astype(str).nunique()),
        "total_iku_unik": int(frame["iku"].dropna().astype(str).replace("-", pd.NA).dropna().nunique()) if "iku" in frame.columns else 0,
        "total_kegiatan_unik": int(frame["kegiatan"].dropna().astype(str).replace("-", pd.NA).dropna().nunique()) if "kegiatan" in frame.columns else 0,
    }


def _series(frame: pd.DataFrame, dimension: str, limit: int | None = None) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    grouped = (
        frame.groupby(dimension, dropna=False)
        .agg(
            nominal_piutang_rp=("nominal_piutang_rp", "sum"),
            jumlah_mhs_penunggak=("jumlah_mhs_penunggak", "sum"),
            debitur_unik=("nim", lambda values: values.dropna().astype(str).nunique()),
        )
        .reset_index()
        .rename(columns={dimension: "label"})
    )
    grouped["label"] = grouped["label"].fillna("-").astype(str)
    grouped = grouped.sort_values(["nominal_piutang_rp", "label"], ascending=[False, True])
    if limit is not None:
        grouped = grouped.head(limit)
    return _records(grouped)


def build_chart_payloads(frame: pd.DataFrame) -> dict[str, Any]:
    trend = _series(frame, "tahun_akademik")
    trend = sorted(trend, key=lambda item: str(item["label"]))
    return {
        "bar_by_tahun_anggaran": {
            "filter_column": "tahun_anggaran",
            "items": _series(frame, "tahun_anggaran"),
        },
        "donut_by_kualitas": {
            "filter_column": "kualitas",
            "items": _series(frame, "kualitas"),
        },
        "bar_by_prodi": {
            "filter_column": "nama_prodi",
            "items": _series(frame, "nama_prodi", limit=12),
        },
        "line_by_tahun_akademik": {
            "filter_column": "tahun_akademik",
            "items": trend,
        },
        "bar_by_semester": {
            "filter_column": "semester",
            "items": _series(frame, "semester"),
        },
        "bar_by_iku": {
            "filter_column": "iku",
            "items": _series(frame, "iku") if "iku" in frame.columns else [],
        },
        "bar_by_kegiatan": {
            "filter_column": "kegiatan",
            "items": _series(frame, "kegiatan") if "kegiatan" in frame.columns else [],
        },
        "bar_by_akun": {
            "filter_column": "akun",
            "items": _series(frame, "akun") if "akun" in frame.columns else [],
        },
    }


def build_detail_table(frame: pd.DataFrame, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    columns = [
        "tahun_akademik",
        "tahun_anggaran",
        "semester",
        "nama_prodi",
        "nama_fakultas",
        "kualitas",
        "item_id",
        "nim",
        "nama_debitur",
        "nominal_piutang_rp",
        "jumlah_mhs_penunggak",
        "iku",
        "kegiatan",
        "akun",
        "mapping_status",
        "uraian_detail",
    ]
    sorted_frame = frame.sort_values("nominal_piutang_rp", ascending=False)
    available_columns = [column for column in columns if column in sorted_frame.columns]
    page = sorted_frame[available_columns].iloc[max(offset, 0) : max(offset, 0) + max(limit, 1)]
    return {
        "columns": columns,
        "rows": _records(page),
        "total_rows": int(len(frame)),
        "limit": int(limit),
        "offset": int(offset),
    }


def build_dashboard_response(args: Any | None = None, section: str = "all", path: Path | None = None) -> dict[str, Any]:
    frame, metadata = load_dashboard_view(path)
    validation = validate_dashboard_columns(frame)
    if frame is None:
        return metadata
    if validation["status"] != "validated":
        return {
            "status": "missing_columns",
            "source": metadata["source"],
            "generated_at": metadata["generated_at"],
            "message": "Gold dashboard view tidak memiliki kolom wajib.",
            "missing_columns": validation["missing_columns"],
            "data": None,
        }

    frame["nominal_piutang_rp"] = pd.to_numeric(frame["nominal_piutang_rp"], errors="coerce").fillna(0)
    frame["jumlah_mhs_penunggak"] = pd.to_numeric(frame["jumlah_mhs_penunggak"], errors="coerce").fillna(0)
    frame = _ensure_analytic_columns(frame)
    filters = _query_filters(args)
    filtered = apply_dashboard_filters(frame, filters)
    status = "empty_after_filter" if filtered.empty else "validated"
    response: dict[str, Any] = {
        "status": status,
        "source": metadata["source"],
        "source_kind": metadata.get("source_kind"),
        "source_dataset": metadata.get("source_dataset"),
        "source_note": metadata.get("source_note"),
        "source_priority": metadata.get("source_priority"),
        "superset_reference": metadata.get("superset_reference"),
        "generated_at": metadata["generated_at"],
        "filters": filters,
        "data": {"labels": metadata.get("labels", PIUTANG_LABELS)},
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
    key = "status" if section == "status" else section
    payload["data"] = data.get(key)
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
