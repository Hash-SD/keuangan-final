from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.rab_parser import parse_rab_workbook


RAB_2023_JAN = Path(r"D:\Downloads\RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx")
RAB_2023_JUL = Path(r"D:\Downloads\RAB_SD_Usulan KE (1)_jul-des 2023.xlsx")


@pytest.mark.skipif(not (RAB_2023_JAN.exists() and RAB_2023_JUL.exists()), reason="sample workbooks not available")
def test_parse_2023_multi_file_periods_merge_without_overwrite():
    frames = []
    for path, periode in [(RAB_2023_JAN, "Jan-Jun"), (RAB_2023_JUL, "Jul-Des")]:
        items, _, _ = parse_rab_workbook(ExcelSource(path=path, tahun_input=2023, periode=periode, prodi="Sains Data", jenis_dataset="rab"))
        frames.append(items)

    merged = pd.concat(frames, ignore_index=True)
    assert len(merged) > 0
    assert set(merged["periode"].dropna().unique()) == {"Jan-Jun", "Jul-Des"}
    assert merged["source_file"].nunique() == 2
    assert merged["item_id"].is_unique
