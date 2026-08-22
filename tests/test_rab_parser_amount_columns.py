from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.parser_flexible.rab_parser import parse_rab_workbook


def _write_workbook(path: Path, *, rekap_total: int, rows: list[tuple[object, ...]]) -> None:
    workbook = Workbook()
    rekap = workbook.active
    rekap.title = "REKAP"
    rekap.cell(row=11, column=5, value="Uraian")
    rekap.cell(row=11, column=8, value="Nominal")
    rekap.cell(row=12, column=5, value="Belanja Uji Parser")
    rekap.cell(row=12, column=8, value=rekap_total)
    rekap.cell(row=36, column=5, value="Total")
    rekap.cell(row=36, column=8, value=rekap_total)

    detail = workbook.create_sheet("SG & Kuliah Tamu")
    headers = [
        "No",
        "Uraian",
        "Suplier",
        "QTY",
        "Satuan",
        "Harga Satuan",
        "Total Sebelum Pajak",
        "PPh 21",
        "PPN [10%]",
        "PPh 22 [1.5%]",
        "PPh 23 [2%]",
        "Jumah diterima",
        "Total",
    ]
    for column_number, value in enumerate(headers, start=1):
        detail.cell(row=12, column=column_number, value=value)
    for row_number, row_values in enumerate(rows, start=13):
        for column_number, value in enumerate(row_values, start=1):
            detail.cell(row=row_number, column=column_number, value=value)

    workbook.save(path)


def test_parser_uses_final_amount_column_not_tax_or_intermediate_total(tmp_path):
    path = tmp_path / "rab_2024_amount_columns.xlsx"
    _write_workbook(
        path,
        rekap_total=6_745_050,
        rows=[
            (1, "KULIAH TAMU Kecerdasan Buatan", None, 2, "Jam", 900_000, 1_800_000, 90_000, 0, 0, 0, 1_710_000, 1_800_000),
            (2, "Cetak Buku Perwalian", None, 297, "Buah", 15_000, 4_455_000, 0, 490_050, 0, 89_100, 4_365_900, 4_945_050),
        ],
    )

    items, _, validation = parse_rab_workbook(
        ExcelSource(path=path, tahun_input=2024, prodi="Sains Data", jenis_dataset="rab")
    )

    assert len(items) == 2
    assert items["jumlah"].isna().sum() == 0
    assert items["uraian_detail"].str.lower().eq("uraian").sum() == 0
    assert int(items["jumlah"].sum()) == 6_745_050

    kuliah_tamu = items[items["uraian_detail"].eq("KULIAH TAMU Kecerdasan Buatan")].iloc[0]
    assert kuliah_tamu["qty"] == 2
    assert kuliah_tamu["harga_satuan"] == 900_000
    assert kuliah_tamu["jumlah"] == 1_800_000

    assert validation.iloc[0]["validation_status"] == "OK"
    assert validation.iloc[0]["total_rekap"] == 6_745_050


def test_parser_defaults_missing_quantity_and_unit_price_to_final_amount(tmp_path):
    path = tmp_path / "rab_missing_detail_values.xlsx"
    _write_workbook(
        path,
        rekap_total=2_520_000,
        rows=[
            (1, "Sewa Bus Kegiatan", None, None, "Paket", None, None, None, None, None, None, None, 2_520_000),
        ],
    )

    items, _, _ = parse_rab_workbook(
        ExcelSource(path=path, tahun_input=2025, prodi="Sains Data", jenis_dataset="rab")
    )

    row = items.iloc[0]
    assert row["qty"] == 1
    assert row["harga_satuan"] == 2_520_000
    assert row["jumlah"] == 2_520_000


def test_parser_matches_2023_period_rekap_totals_without_header_rows(tmp_path):
    jan_path = tmp_path / "rab_2023_jan_jun.xlsx"
    jul_path = tmp_path / "rab_2023_jul_des.xlsx"
    _write_workbook(
        jan_path,
        rekap_total=37_000_000,
        rows=[
            (1, "Belanja Bahan Januari", None, 1, "Paket", 4_950_000, 4_500_000, 0, 450_000, 0, 0, 4_500_000, 4_950_000),
            (2, "Belanja Non Ops Januari", None, 1, "Paket", 32_050_000, 32_050_000, 0, 0, 0, 0, 32_050_000, 32_050_000),
        ],
    )
    _write_workbook(
        jul_path,
        rekap_total=90_027_000,
        rows=[
            (1, "Belanja Bahan Semester 2", None, 1, "Paket", 37_075_000, 37_075_000, 0, 0, 0, 0, 37_075_000, 37_075_000),
            (2, "Belanja Sewa Semester 2", None, 1, "Paket", 15_792_000, 14_100_000, 0, 1_410_000, 0, 282_000, 12_408_000, 15_792_000),
            (3, "Belanja Lainnya Semester 2", None, 1, "Paket", 37_160_000, 37_160_000, 0, 0, 0, 0, 37_160_000, 37_160_000),
        ],
    )

    frames = []
    validations = []
    for path, periode in [(jan_path, "Jan-Jun"), (jul_path, "Jul-Des")]:
        items, _, validation = parse_rab_workbook(
            ExcelSource(path=path, tahun_input=2023, periode=periode, prodi="Sains Data", jenis_dataset="rab")
        )
        frames.append(items)
        validations.append(validation)

    merged = pd.concat(frames, ignore_index=True)
    validation_df = pd.concat(validations, ignore_index=True)

    assert len(merged) == 5
    assert int(merged["jumlah"].sum()) == 127_027_000
    assert merged["jumlah"].isna().sum() == 0
    assert merged["uraian_detail"].str.lower().eq("uraian").sum() == 0
    assert not merged["jumlah"].between(0.000001, 1000).any()
    assert validation_df["validation_status"].tolist() == ["OK", "OK"]
