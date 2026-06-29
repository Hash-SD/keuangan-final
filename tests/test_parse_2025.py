from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.rab_parser import parse_rab_workbook


RAB_2025 = Path(r"D:\Downloads\RAB 2025 SD RAB IKU.xlsx")


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_parse_2025_rab_color_hierarchy_items():
    items, hierarchy, validation = parse_rab_workbook(ExcelSource(path=RAB_2025, tahun_input=2025, prodi="Sains Data", jenis_dataset="rab"))

    assert len(items) > 0
    assert {"item_id", "kegiatan", "kode_akun", "uraian_detail", "jumlah", "source_sheet", "source_row"}.issubset(items.columns)
    assert items["source_sheet"].eq("RAB").any()
    assert hierarchy["row_type"].isin(["NOMENKLATUR", "KEGIATAN", "UNIT", "AKUN"]).any()
    assert not validation.empty
