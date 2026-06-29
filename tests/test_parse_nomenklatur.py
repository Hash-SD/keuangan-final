from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.nomenklatur_parser import parse_nomenklatur_workbook


NOMENKLATUR = Path(r"D:\Downloads\Nomenklatur.xlsx")


@pytest.mark.skipif(not NOMENKLATUR.exists(), reason="sample workbook not available")
def test_parse_nomenklatur_builds_detail_and_iku_bridge():
    detail, bridge, warnings = parse_nomenklatur_workbook(ExcelSource(path=NOMENKLATUR, tahun_input=2026, prodi="Sains Data", jenis_dataset="nomenklatur"))

    assert len(detail) > 0
    assert {"detail_id", "nomenklatur_path", "nomenklatur_key", "detail_kegiatan"}.issubset(detail.columns)
    assert detail["nomenklatur_path"].notna().any()
    assert {"detail_id", "iku_kode", "allocation_weight"}.issubset(bridge.columns)
    assert not warnings.empty
