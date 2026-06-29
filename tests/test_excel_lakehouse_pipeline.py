from __future__ import annotations

from pathlib import Path

import pytest

from src.excel_ingestion.excel_cell_extractor import ExcelSource
from src.transformations import excel_lakehouse_pipeline


FILES = [
    Path(r"D:\Downloads\RAB 2025 SD RAB IKU.xlsx"),
    Path(r"D:\Downloads\Nomenklatur.xlsx"),
    Path(r"D:\Downloads\Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx"),
    Path(r"D:\Downloads\RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx"),
    Path(r"D:\Downloads\RAB_SD_Usulan KE (1)_jul-des 2023.xlsx"),
]


@pytest.mark.skipif(not all(path.exists() for path in FILES), reason="sample workbooks not available")
def test_excel_lakehouse_pipeline_writes_bronze_silver_gold_parquet(tmp_path, monkeypatch):
    generated = tmp_path / "generated"
    monkeypatch.setattr(excel_lakehouse_pipeline, "GENERATED_DIR", generated)
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_dataset_pointer", lambda: {"session_id": "test-session"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_period_metadata", lambda: {"target_tahun_anggaran": "2025", "target_prodi": "Sains Data"})
    sources = [
        ExcelSource(path=FILES[0], tahun_input=2025, prodi="Sains Data", jenis_dataset="rab"),
        ExcelSource(path=FILES[1], tahun_input=2026, prodi="Sains Data", jenis_dataset="nomenklatur"),
        ExcelSource(path=FILES[2], tahun_input=2024, prodi="Sains Data", jenis_dataset="rab"),
        ExcelSource(path=FILES[3], tahun_input=2023, periode="Jan-Jun", prodi="Sains Data", jenis_dataset="rab"),
        ExcelSource(path=FILES[4], tahun_input=2023, periode="Jul-Des", prodi="Sains Data", jenis_dataset="rab"),
    ]

    result = excel_lakehouse_pipeline.run_excel_lakehouse_pipeline(sources)

    assert result["bronze_cells"] > 0
    assert result["silver_rab_items"] > 0
    assert result["silver_nomenklatur_detail"] > 0
    assert result["fact_anggaran_rows"] > 0
    assert (generated / "bronze" / "bronze_excel_cells.parquet").exists()
    assert (generated / "silver" / "silver_rab_items_flexible.parquet").exists()
    assert (generated / "silver" / "silver_nomenklatur_detail.parquet").exists()
    assert (generated / "gold" / "fact_anggaran.parquet").exists()
