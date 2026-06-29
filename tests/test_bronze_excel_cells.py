from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource, extract_excel_cells


NOMENKLATUR = Path(r"D:\Downloads\Nomenklatur.xlsx")


@pytest.mark.skipif(not NOMENKLATUR.exists(), reason="sample workbook not available")
def test_bronze_excel_cells_extracts_value_color_merge_and_lineage():
    df = extract_excel_cells(ExcelSource(path=NOMENKLATUR, tahun_input=2026, prodi="Sains Data", jenis_dataset="nomenklatur"), run_id="test-run")

    assert not df.empty
    assert {"source_file", "sheet_name", "row_number", "column_number", "cell_value", "fill_color", "is_merged", "merged_range"}.issubset(df.columns)
    assert df["fill_color"].notna().any()
    assert df["is_merged"].any()
    assert set(df["source_file"].unique()) == {NOMENKLATUR.name}
