from __future__ import annotations

import re

import pandas as pd


def normalize_key(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_mapping_table(items: pd.DataFrame, nomenklatur: pd.DataFrame | None = None) -> pd.DataFrame:
    if items.empty:
        return pd.DataFrame(columns=["mapping_subject", "source_value", "target_value", "mapping_method", "mapping_status", "mapping_note"])
    rows: list[dict[str, object]] = []
    for column, subject in [("kode_akun", "akun"), ("kegiatan", "kegiatan"), ("iku", "iku")]:
        if column not in items.columns:
            continue
        for value in sorted({str(item) for item in items[column].dropna() if str(item).strip()}):
            rows.append(
                {
                    "mapping_subject": subject,
                    "source_value": value,
                    "target_value": value,
                    "mapping_method": "exact_or_source",
                    "mapping_status": "exact_match" if subject == "akun" and re.search(r"\b\d{6}\b", value) else "reviewable_source",
                    "mapping_note": "Generated from parsed source. Manual curation can override this row.",
                }
            )
    if nomenklatur is not None and not nomenklatur.empty and "detail_kegiatan" in nomenklatur.columns:
        for value in sorted({str(item) for item in nomenklatur["detail_kegiatan"].dropna() if str(item).strip()}):
            rows.append(
                {
                    "mapping_subject": "nomenklatur",
                    "source_value": value,
                    "target_value": value,
                    "mapping_method": "nomenklatur_master",
                    "mapping_status": "master_reference",
                    "mapping_note": "Generated from Nomenklatur workbook detail.",
                }
            )
    return pd.DataFrame(rows).drop_duplicates()
