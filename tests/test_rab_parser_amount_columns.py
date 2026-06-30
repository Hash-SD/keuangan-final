from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.rab_parser import parse_rab_workbook


LOCAL_SAMPLE_DIR = Path(
    "data/raw/excel_lakehouse/upload-2026-06-09-011818-37cc4d/"
    "239ab80c-8350-4b03-8943-f5308ed3b595"
)
RAB_2024 = LOCAL_SAMPLE_DIR / "Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx"
RAB_2023_JAN = LOCAL_SAMPLE_DIR / "RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx"
RAB_2023_JUL = LOCAL_SAMPLE_DIR / "RAB_SD_Usulan KE (1)_jul-des 2023.xlsx"


@pytest.mark.skipif(not RAB_2024.exists(), reason="local uploaded 2024 workbook not available")
def test_2024_parser_uses_final_amount_column_not_tax_or_intermediate_total():
    items, _, validation = parse_rab_workbook(
        ExcelSource(path=RAB_2024, tahun_input=2024, prodi="Sains Data", jenis_dataset="rab")
    )

    assert len(items) == 113
    assert items["jumlah"].isna().sum() == 0
    assert items["uraian_detail"].str.lower().eq("uraian").sum() == 0
    assert int(items["jumlah"].sum()) == 154_588_390

    kuliah_tamu = items[
        items["raw_row_text"].astype(str).str.contains("KULIAH TAMU Kecerdasan Buatan", case=False, na=False)
    ]
    assert len(kuliah_tamu) == 1
    assert kuliah_tamu.iloc[0]["qty"] == 2
    assert kuliah_tamu.iloc[0]["harga_satuan"] == 900_000
    assert kuliah_tamu.iloc[0]["jumlah"] == 1_800_000

    assert validation.iloc[0]["validation_status"] == "REVIEW"
    assert validation.iloc[0]["total_rekap"] == 164_849_800


@pytest.mark.skipif(
    not (RAB_2023_JAN.exists() and RAB_2023_JUL.exists()),
    reason="local uploaded 2023 workbooks not available",
)
def test_2023_parser_matches_period_rekap_totals_without_header_rows():
    frames = []
    validations = []
    for path, periode in [(RAB_2023_JAN, "Jan-Jun"), (RAB_2023_JUL, "Jul-Des")]:
        items, _, validation = parse_rab_workbook(
            ExcelSource(path=path, tahun_input=2023, periode=periode, prodi="Sains Data", jenis_dataset="rab")
        )
        frames.append(items)
        validations.append(validation)

    merged = pd.concat(frames, ignore_index=True)
    validation_df = pd.concat(validations, ignore_index=True)

    assert len(merged) == 62
    assert int(merged["jumlah"].sum()) == 127_027_000
    assert merged["jumlah"].isna().sum() == 0
    assert merged["uraian_detail"].str.lower().eq("uraian").sum() == 0
    assert not merged["jumlah"].between(0.000001, 1000).any()
    assert validation_df["validation_status"].tolist() == ["OK", "OK"]
