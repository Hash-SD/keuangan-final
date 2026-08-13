from __future__ import annotations

import re

import pandas as pd

from .contract import FACT_COLUMNS

UNCLASSIFIED_IKU_LABEL = "IKU belum terklasifikasi"


def _split_iku(value: object) -> list[str]:
    if value is None or pd.isna(value):
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [part.strip() for part in re.split(r";|,|\n", text) if part.strip()]
    return parts


def build_fact_anggaran(silver_items: pd.DataFrame) -> pd.DataFrame:
    if silver_items.empty:
        return pd.DataFrame(columns=FACT_COLUMNS)
    source = silver_items.copy()
    if {"source_file", "source_role"}.issubset(source.columns):
        source_role = source["source_role"].fillna("").astype(str)
        files_with_main_rab = set(source.loc[source_role.eq("main_rab"), "source_file"].dropna().astype(str))
        if files_with_main_rab:
            source_file = source["source_file"].fillna("").astype(str)
            source = source[~source_file.isin(files_with_main_rab) | source_role.eq("main_rab")]
    elif "source_role" in source.columns and source["source_role"].fillna("").astype(str).eq("main_rab").any():
        source = source[source["source_role"].fillna("").astype(str).eq("main_rab")]
    if "include_in_gold" in source.columns:
        source = source[source["include_in_gold"].fillna(False).astype(bool)]
    if "row_type" in source.columns:
        source = source[~source["row_type"].fillna("").astype(str).isin(["subtotal_row", "subtotal_or_header", "total_row", "orphan_leaf_item", "blank_or_note"])]
    rows: list[dict[str, object]] = []
    for _, item in source.iterrows():
        jumlah = pd.to_numeric(pd.Series([item.get("jumlah")]), errors="coerce").iloc[0]
        if pd.isna(jumlah):
            continue
        iku_values = _split_iku(item.get("iku"))
        if not iku_values:
            iku_values = [None]
        weight = 1 / len(iku_values)
        for iku in iku_values:
            iku_label = iku or UNCLASSIFIED_IKU_LABEL
            rows.append(
                {
                    "item_id": item.get("item_id"),
                    "dataset_session_id": item.get("dataset_session_id"),
                    "run_id": item.get("run_id"),
                    "tahun": item.get("tahun"),
                    "prodi": item.get("prodi"),
                    "fakultas": item.get("fakultas"),
                    "kegiatan": item.get("kegiatan"),
                    "cluster_kegiatan": item.get("cluster_kegiatan") or item.get("kegiatan") or item.get("nomenklatur_path"),
                    "akun": item.get("akun") or item.get("nama_akun"),
                    "kode_akun": item.get("kode_akun"),
                    "nama_akun": item.get("nama_akun"),
                    "nama_akun_asli": item.get("nama_akun_asli"),
                    "iku": iku_label,
                    "kode_iku": iku or UNCLASSIFIED_IKU_LABEL,
                    "nama_iku": item.get("nama_iku") or iku_label,
                    "nomenklatur_path": item.get("nomenklatur_path"),
                    "uraian_detail": item.get("uraian_detail"),
                    "qty": item.get("qty"),
                    "satuan": item.get("satuan"),
                    "harga_satuan": item.get("harga_satuan"),
                    "jumlah": jumlah,
                    "jumlah_weighted_iku": jumlah * weight if pd.notna(jumlah) else None,
                    "allocation_weight": weight,
                    "mapping_status": item.get("mapping_status"),
                    "data_quality_flag": item.get("data_quality_flag"),
                    "source_file": item.get("source_file"),
                    "source_sheet": item.get("source_sheet"),
                    "source_row": item.get("source_row"),
                    "source_role": item.get("source_role"),
                    "row_type": item.get("row_type"),
                    "quality_flags": item.get("quality_flags"),
                    "created_at": item.get("created_at"),
                }
            )
    fact = pd.DataFrame(rows)
    return fact[FACT_COLUMNS]
