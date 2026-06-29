from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.rab_parser import parse_rab_workbook


RAB_2024 = Path(r"D:\Downloads\Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx")


@pytest.mark.skipif(not RAB_2024.exists(), reason="sample workbook not available")
def test_parse_2024_detail_sheets_keep_lineage():
    items, _, validation = parse_rab_workbook(ExcelSource(path=RAB_2024, tahun_input=2024, prodi="Sains Data", jenis_dataset="rab"))

    assert len(items) > 0
    assert items["tahun"].astype(str).eq("2024").any()
    assert items["source_sheet"].nunique() > 1
    assert {"source_file", "source_sheet", "source_row", "data_quality_flag"}.issubset(items.columns)
    assert not validation.empty
