from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource, extract_excel_cells
from src.gold.fact_anggaran import build_fact_anggaran
from src.parser_flexible.rab_parser import classify_sheet_role, parse_rab_workbook


RAB_2025 = Path(r"D:\Downloads\RAB 2025 SD RAB IKU.xlsx")


def _source() -> ExcelSource:
    return ExcelSource(path=RAB_2025, tahun_input=2025, prodi="Sains Data", jenis_dataset="rab")


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_rab_2025_total_matches_expected():
    items, _, _ = parse_rab_workbook(_source())
    fact = build_fact_anggaran(items)

    assert items[items["source_role"].eq("main_rab")]["jumlah"].sum() == 236_046_266
    assert items[items["include_in_gold"].eq(True)]["jumlah"].sum() == 235_746_266
    assert fact["jumlah_weighted_iku"].sum() == 235_746_266


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_orphan_row_16_is_excluded():
    items, _, _ = parse_rab_workbook(_source())

    orphan = items[items["row_type"].eq("orphan_leaf_item")]

    assert orphan["source_row"].tolist() == [16]
    assert orphan["jumlah"].tolist() == [300_000]
    assert orphan["include_in_gold"].tolist() == [False]
    assert "orphan_not_in_parent_sum" in orphan.iloc[0]["quality_flags"]


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_subtotal_rows_are_not_in_gold():
    items, _, _ = parse_rab_workbook(_source())
    fact = build_fact_anggaran(items)

    assert not fact["row_type"].isin(["subtotal_row", "subtotal_or_header", "total_row", "orphan_leaf_item"]).any()
    assert fact["source_role"].eq("main_rab").all()


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_detail_support_sheets_do_not_double_count():
    items, _, _ = parse_rab_workbook(_source())
    fact = build_fact_anggaran(items)
    detail_support = items[items["source_role"].eq("detail_support")]

    assert detail_support["jumlah"].sum() == 394_248_049
    assert detail_support["include_in_gold"].eq(False).all()
    assert fact["source_role"].eq("detail_support").sum() == 0


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_formula_ref_error_detected():
    _, _, validation = parse_rab_workbook(_source())
    formula_errors = validation[validation["validation_type"].eq("FORMULA_ERROR")]

    assert not formula_errors.empty
    assert formula_errors["formula_error"].eq("#REF!").any()


@pytest.mark.skipif(not RAB_2025.exists(), reason="sample workbook not available")
def test_excel_visual_metadata_is_preserved_in_bronze():
    bronze = extract_excel_cells(_source(), run_id="test-run")

    expected_columns = {
        "formula",
        "number_format",
        "fill_type",
        "fill_fg_rgb",
        "fill_fg_indexed",
        "font_bold",
        "border_bottom_style",
        "alignment_horizontal",
        "is_merged_cell",
        "merged_range",
    }
    assert expected_columns.issubset(bronze.columns)
    assert bronze["sheet_name"].eq("RAB").any()


def test_excel_sheet_role_classifier():
    assert classify_sheet_role("RAB") == "main_rab"
    assert classify_sheet_role("jasa profesi - ok") == "detail_support"
    assert classify_sheet_role("belanja bahan") == "detail_support"
    assert classify_sheet_role("RPD") == "mapping_or_reference"
