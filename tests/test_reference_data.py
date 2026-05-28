from pathlib import Path

import pandas as pd
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]


def test_master_ukt_spi_reference_shapes():
    ukt = pd.read_csv(ROOT / "data" / "generated" / "master_ukt_itera.csv")
    spi = pd.read_csv(ROOT / "data" / "generated" / "master_spi_itera.csv")
    assert len(ukt) == 328
    assert len(spi) == 41
    sains_data_gol8 = ukt[(ukt["prodi"] == "Sains Data") & (ukt["golongan_ukt"] == "Gol. 8")].iloc[0]
    assert int(sains_data_gol8["nominal_ukt"]) == 9_500_000
    sains_data_spi = spi[spi["prodi"] == "Sains Data"].iloc[0]
    assert int(sains_data_spi["nominal_spi"]) == 30_000_000


def test_master_biaya_excel_sheets():
    workbook = load_workbook(ROOT / "data" / "raw" / "excel" / "master_biaya_itera.xlsx", read_only=True)
    assert workbook.sheetnames == ["UKT_Wide", "UKT_Long", "SPI", "Metadata"]
