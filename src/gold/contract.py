"""Canonical contract for the annual, allocation-grain Gold dataset.

The physical Gold layer is a star schema (4 dimension tables + 1 fact table
with FK integers).  ``gold.vw_fact_anggaran`` reconstructs the flat
denormalized view via JOIN for backward-compatible consumers (Superset,
portal).  ``fact_anggaran.csv`` on disk is the flat reconstructed output.
"""

from __future__ import annotations

from typing import Iterable


FACT_COLUMNS = [
    "item_id",
    "dataset_session_id",
    "run_id",
    "tahun",
    "prodi",
    "fakultas",
    "kegiatan",
    "cluster_kegiatan",
    "akun",
    "kode_akun",
    "nama_akun",
    "nama_akun_asli",
    "iku",
    "kode_iku",
    "nama_iku",
    "nomenklatur_path",
    "uraian_detail",
    "qty",
    "satuan",
    "harga_satuan",
    "jumlah",
    "allocation_weight",
    "jumlah_weighted_iku",
    "mapping_status",
    "data_quality_flag",
    "source_file",
    "source_sheet",
    "source_row",
    "source_role",
    "row_type",
    "quality_flags",
    "created_at",
]

GOLD_SQL_TYPES = {
    "item_id": "TEXT",
    "dataset_session_id": "TEXT",
    "run_id": "TEXT",
    "tahun": "TEXT",
    "prodi": "TEXT",
    "fakultas": "TEXT",
    "kegiatan": "TEXT",
    "cluster_kegiatan": "TEXT",
    "akun": "TEXT",
    "kode_akun": "TEXT",
    "nama_akun": "TEXT",
    "nama_akun_asli": "TEXT",
    "iku": "TEXT",
    "kode_iku": "TEXT",
    "nama_iku": "TEXT",
    "nomenklatur_path": "TEXT",
    "uraian_detail": "TEXT",
    "qty": "DOUBLE PRECISION",
    "satuan": "TEXT",
    "harga_satuan": "DOUBLE PRECISION",
    "jumlah": "DOUBLE PRECISION",
    "allocation_weight": "DOUBLE PRECISION",
    "jumlah_weighted_iku": "DOUBLE PRECISION",
    "mapping_status": "TEXT",
    "data_quality_flag": "TEXT",
    "source_file": "TEXT",
    "source_sheet": "TEXT",
    "source_row": "INTEGER",
    "source_role": "TEXT",
    "row_type": "TEXT",
    "quality_flags": "TEXT",
    "created_at": "TIMESTAMPTZ",
}

# ── Star schema contract ──────────────────────────────────────────────
# Physical tables in Postgres/Trino. ``tahun`` stays denormalized in fact.

STAR_FACT_COLUMNS = [
    "fact_key",
    "item_id",
    "dataset_session_id",
    "run_id",
    "tahun",
    "org_key",
    "kegiatan_key",
    "akun_key",
    "iku_key",
    "uraian_detail",
    "satuan",
    "qty",
    "harga_satuan",
    "jumlah",
    "allocation_weight",
    "jumlah_weighted_iku",
    "mapping_status",
    "data_quality_flag",
    "source_file",
    "source_sheet",
    "source_row",
    "source_role",
    "row_type",
    "quality_flags",
    "created_at",
]

STAR_DIM_SPEC: dict[str, dict[str, list[str]]] = {
    "dim_organisasi": {"key": "org_key", "natural": ["prodi", "fakultas"]},
    "dim_kegiatan": {
        "key": "kegiatan_key",
        "natural": ["kegiatan", "cluster_kegiatan", "nomenklatur_path"],
    },
    "dim_akun": {
        "key": "akun_key",
        "natural": ["akun", "kode_akun", "nama_akun", "nama_akun_asli"],
    },
    "dim_iku": {"key": "iku_key", "natural": ["iku", "kode_iku", "nama_iku"]},
}

STAR_SQL_TYPES: dict[str, str] = {
    "fact_key": "SERIAL",
    "item_id": "TEXT",
    "dataset_session_id": "TEXT",
    "run_id": "TEXT",
    "tahun": "TEXT",
    "org_key": "INTEGER",
    "kegiatan_key": "INTEGER",
    "akun_key": "INTEGER",
    "iku_key": "INTEGER",
    "uraian_detail": "TEXT",
    "satuan": "TEXT",
    "qty": "DOUBLE PRECISION",
    "harga_satuan": "DOUBLE PRECISION",
    "jumlah": "DOUBLE PRECISION",
    "allocation_weight": "DOUBLE PRECISION",
    "jumlah_weighted_iku": "DOUBLE PRECISION",
    "mapping_status": "TEXT",
    "data_quality_flag": "TEXT",
    "source_file": "TEXT",
    "source_sheet": "TEXT",
    "source_row": "INTEGER",
    "source_role": "TEXT",
    "row_type": "TEXT",
    "quality_flags": "TEXT",
    "created_at": "TIMESTAMPTZ",
}

DASHBOARD_FILTERS = ("tahun", "prodi", "iku", "kegiatan", "akun")

GOLD_METRICS = [
    {
        "key": "total_anggaran",
        "label": "Total Anggaran",
        "aggregation": "SUM",
        "column": "jumlah_weighted_iku",
        "expression": "SUM(jumlah_weighted_iku)",
    },
    {
        "key": "jumlah_item",
        "label": "Jumlah Item",
        "aggregation": "COUNT_DISTINCT",
        "column": "item_id",
        "expression": "COUNT(DISTINCT item_id)",
    },
    {
        "key": "jumlah_iku",
        "label": "Jumlah IKU",
        "aggregation": "COUNT_DISTINCT",
        "column": "kode_iku",
        "expression": "COUNT(DISTINCT kode_iku)",
    },
    {
        "key": "jumlah_kegiatan",
        "label": "Jumlah Kegiatan",
        "aggregation": "COUNT_DISTINCT",
        "column": "kegiatan",
        "expression": "COUNT(DISTINCT kegiatan)",
    },
    {
        "key": "status_rekonsiliasi",
        "label": "Status Rekonsiliasi",
        "aggregation": "STATUS",
        "column": "status",
        "expression": None,
        "source": "gold.vw_dashboard_reconciliation",
    },
]

GOLD_GRAIN = "satu item anggaran x satu alokasi IKU"

ANNUAL_SOURCE_RULES = (
    "Semua sumber harus memiliki tahun anggaran.",
    "Satu workbook tahunan digunakan bila menjadi satu-satunya sumber tahun tersebut.",
    "Workbook parsial pada tahun yang sama digabung bila identitas sumber tidak tumpang tindih.",
    "Workbook tahunan dan parsial harus direkonsiliasi; overlap yang belum terbukti dihentikan sebagai AMBIGUOUS_SOURCE_OVERLAP.",
    "Identitas sumber memakai item_id, source_file, source_sheet, source_row, dan dataset_session_id.",
)


def validate_fact_columns(columns: Iterable[str]) -> dict[str, list[str] | bool]:
    """Return a deterministic schema comparison for a Gold dataframe."""

    actual = list(columns)
    expected = list(FACT_COLUMNS)
    missing = [column for column in expected if column not in actual]
    unexpected = [column for column in actual if column not in expected]
    return {
        "valid": actual == expected,
        "missing": missing,
        "unexpected": unexpected,
    }
