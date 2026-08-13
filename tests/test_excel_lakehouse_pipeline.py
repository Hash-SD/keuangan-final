from __future__ import annotations

import json
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
    monkeypatch.setattr(excel_lakehouse_pipeline, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(excel_lakehouse_pipeline, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_dataset_pointer", lambda: {"session_id": "test-session"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_period_metadata", lambda: {"target_tahun_anggaran": "2025", "target_prodi": "Sains Data"})
    monkeypatch.setenv("PIPELINE_RUN_ID", "pipeline-test-run")
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
    run_root = generated / "bronze" / "test-session" / "pipeline-test-run"
    assert (run_root / "bronze_excel_cells.parquet").exists()
    assert (generated / "silver" / "test-session" / "pipeline-test-run" / "silver_rab_items_flexible.parquet").exists()
    assert (generated / "silver" / "test-session" / "pipeline-test-run" / "silver_nomenklatur_detail.parquet").exists()
    assert (generated / "gold" / "test-session" / "pipeline-test-run" / "fact_anggaran.parquet").exists()
    metadata = json.loads((generated / "excel_lakehouse_metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "PUBLISHED"


def test_discover_excel_sources_prefers_complete_uploaded_multiyear_bundle(tmp_path, monkeypatch):
    raw_root = tmp_path / "data" / "raw" / "excel_lakehouse"
    bundle = raw_root / "upload-2026-06-09-011818-37cc4d" / "67b436e8-d489-43b1-9747-0f063424e6b4"
    bundle.mkdir(parents=True)
    filenames = [
        "RAB 2025 SD RAB IKU.xlsx",
        "Nomenklatur.xlsx",
        "Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx",
        "RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx",
        "RAB_SD_Usulan KE (1)_jul-des 2023.xlsx",
    ]
    for filename in filenames:
        (bundle / filename).write_bytes(b"placeholder")
    monkeypatch.delenv("FINANCE_EXCEL_FILES", raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setattr(excel_lakehouse_pipeline, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_lakehouse_pipeline, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_dataset_pointer", lambda: {"session_id": "test-session"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_period_metadata", lambda: {"target_tahun_anggaran": "2025", "target_prodi": "Sains Data"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "raw_rab_path", lambda: tmp_path / "missing.xlsx")

    sources = excel_lakehouse_pipeline.discover_excel_sources()

    assert [source.path.name for source in sources] == filenames
    assert [str(source.tahun_input) for source in sources] == ["2025", "2025", "2024", "2023", "2023"]
    assert [source.periode for source in sources] == ["Tahunan", "Tahunan", "Tahunan", "Jan-Jun", "Jul-Des"]


def test_discover_excel_sources_prefers_active_upload_over_old_bundle(tmp_path, monkeypatch):
    raw_root = tmp_path / "data" / "raw" / "excel_lakehouse"
    old_bundle = raw_root / "old-session" / "old-run"
    old_bundle.mkdir(parents=True)
    for filename in [
        "RAB 2025 SD RAB IKU.xlsx",
        "Nomenklatur.xlsx",
        "Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx",
        "RAB_SD_Usulan KE (1)_Jan-Jun 2023.xlsx",
        "RAB_SD_Usulan KE (1)_jul-des 2023.xlsx",
    ]:
        (old_bundle / filename).write_bytes(b"placeholder")
    active_file = raw_root / "2024" / "active-dataset" / "Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx"
    active_file.parent.mkdir(parents=True)
    active_file.write_bytes(b"placeholder")
    active_pointer = tmp_path / "outputs" / "reports" / "active_excel_lakehouse_dataset.json"
    active_pointer.parent.mkdir(parents=True)
    active_pointer.write_text(
        '{"status":"committed","prodi":"Sains Data","tahun_input":"2024","files":[{"path":"data/raw/excel_lakehouse/2024/active-dataset/Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx","jenis_dataset":"rab"}]}',
        encoding="utf-8",
    )
    monkeypatch.delenv("FINANCE_EXCEL_FILES", raising=False)
    monkeypatch.setattr(excel_lakehouse_pipeline, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(excel_lakehouse_pipeline, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(excel_lakehouse_pipeline, "ACTIVE_EXCEL_DATASET_PATH", active_pointer)
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_dataset_pointer", lambda: {"session_id": "test-session"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "active_period_metadata", lambda: {"target_tahun_anggaran": "2025", "target_prodi": "Sains Data"})
    monkeypatch.setattr(excel_lakehouse_pipeline, "raw_rab_path", lambda: tmp_path / "missing.xlsx")

    sources = excel_lakehouse_pipeline.discover_excel_sources()

    assert [source.path.name for source in sources] == ["Rencana Anggaran Prodi Sains Data Tahun 2024.xlsx"]
    assert str(sources[0].tahun_input) == "2024"


def test_2025_parser_excludes_template_example_sheets():
    if not FILES[0].exists():
        pytest.skip("sample workbook not available")

    items, _, _ = excel_lakehouse_pipeline.parse_rab_workbook(ExcelSource(path=FILES[0], tahun_input=2025, prodi="Sains Data", jenis_dataset="rab"))

    assert not items["source_sheet"].str.lower().str.startswith("contoh").any()


def test_infer_year_from_filename_accepts_underscore_delimiters():
    assert excel_lakehouse_pipeline._infer_year_from_filename(Path("RAB_2025_SD_RAB_IKU.xlsx")) == "2025"
    assert excel_lakehouse_pipeline._infer_year_from_filename(Path("RAB_SD_Usulan_KE_1_Jan-Jun_2023.xlsx")) == "2023"
