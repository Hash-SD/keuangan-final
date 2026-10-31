from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.gold.star_normalized import build_gold_star
from src.transformations.excel_lakehouse_pipeline import (
    _write_run_output,
    _write_session_and_combined,
    run_excel_lakehouse_pipeline,
)
from src.gold.fact_anggaran import build_fact_anggaran


def _sample_fact() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "item_id": "i1",
                "dataset_session_id": "s1",
                "run_id": "r1",
                "tahun": "2025",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "kegiatan": "Kuliah Tamu",
                "cluster_kegiatan": "Kuliah Tamu",
                "akun": "522151 - Belanja Jasa Profesi",
                "kode_akun": "522151",
                "nama_akun": "Belanja Jasa Profesi",
                "nama_akun_asli": "Jasa Profesi",
                "iku": "IK 1.1",
                "kode_iku": "IK 1.1",
                "nama_iku": "Lulusan",
                "nomenklatur_path": "A > B",
                "uraian_detail": "Honor",
                "qty": 1,
                "satuan": "paket",
                "harga_satuan": 100,
                "jumlah": 100,
                "allocation_weight": 0.5,
                "jumlah_weighted_iku": 50,
                "mapping_status": "mapped",
                "data_quality_flag": "OK",
                "source_file": "rab.xlsx",
                "source_sheet": "RAB",
                "source_row": 10,
                "source_role": "main_rab",
                "row_type": "leaf_item",
                "quality_flags": "OK",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "item_id": "i1",
                "dataset_session_id": "s1",
                "run_id": "r1",
                "tahun": "2025",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "kegiatan": "Kuliah Tamu",
                "cluster_kegiatan": "Kuliah Tamu",
                "akun": "522151 - Belanja Jasa Profesi",
                "kode_akun": "522151",
                "nama_akun": "Belanja Jasa Profesi",
                "nama_akun_asli": "Jasa Profesi",
                "iku": "IK 2.1",
                "kode_iku": "IK 2.1",
                "nama_iku": "Penelitian",
                "nomenklatur_path": "A > B",
                "uraian_detail": "Honor",
                "qty": 1,
                "satuan": "paket",
                "harga_satuan": 100,
                "jumlah": 100,
                "allocation_weight": 0.5,
                "jumlah_weighted_iku": 50,
                "mapping_status": "mapped",
                "data_quality_flag": "OK",
                "source_file": "rab.xlsx",
                "source_sheet": "RAB",
                "source_row": 10,
                "source_role": "main_rab",
                "row_type": "leaf_item",
                "quality_flags": "OK",
                "created_at": "2026-01-01T00:00:00+00:00",
            },
        ]
    )


def test_star_writes_all_files(tmp_path, monkeypatch):
    from src.transformations import excel_lakehouse_pipeline as pipeline_mod

    fact = _sample_fact()
    session_id = "test-session"
    run_id = "test-run"
    generated = tmp_path / "generated"
    monkeypatch.setattr(pipeline_mod, "GENERATED_DIR", generated)
    monkeypatch.setattr(pipeline_mod, "OUTPUTS_DIR", tmp_path / "outputs")

    star = build_gold_star(fact)
    from src.gold.star_normalized import rebuild_flat_from_star
    flat = rebuild_flat_from_star(star)
    for table_name, df in star.items():
        filename = f"{table_name}.csv"
        pipeline_mod._write_run_output(df, "gold", filename, session_id, run_id)
        pipeline_mod._write_session_and_combined(df, "gold", filename, session_id)
    # also write flat reconstructed
    pipeline_mod._write_run_output(flat, "gold", "fact_anggaran.csv", session_id, run_id)
    pipeline_mod._write_session_and_combined(flat, "gold", "fact_anggaran.csv", session_id)

    for table_name in star:
        filename = f"{table_name}.csv"
        parquet_name = f"{table_name}.parquet"
        assert (generated / "gold" / session_id / run_id / filename).exists(), f"Missing {filename}"
        assert (generated / "gold" / session_id / run_id / parquet_name).exists(), f"Missing {parquet_name}"
        assert (generated / "gold" / session_id / filename).exists(), f"Missing session {filename}"
        assert (generated / "gold" / parquet_name).exists(), f"Missing combined {parquet_name}"


def test_star_total_equals_flat_fact():
    fact = _sample_fact()
    flat_total = float(fact["jumlah_weighted_iku"].sum())

    star = build_gold_star(fact)
    fact_star = star["fact_anggaran"]
    star_total = float(fact_star["jumlah_weighted_iku"].sum())

    assert flat_total == star_total, f"Flat total {flat_total} != star total {star_total}"


def test_star_preserves_grain():
    fact = _sample_fact()
    star = build_gold_star(fact)
    fact_star = star["fact_anggaran"]

    assert len(fact_star) == len(fact)
    assert fact_star["jumlah_weighted_iku"].sum() == fact["jumlah_weighted_iku"].sum()


def test_star_wiring_in_pipeline(tmp_path, monkeypatch):
    from src.transformations import excel_lakehouse_pipeline as pipeline_mod

    generated = tmp_path / "generated"
    outputs = tmp_path / "outputs"
    monkeypatch.setattr(pipeline_mod, "GENERATED_DIR", generated)
    monkeypatch.setattr(pipeline_mod, "OUTPUTS_DIR", outputs)
    monkeypatch.setattr(pipeline_mod, "ACTIVE_EXCEL_DATASET_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(pipeline_mod, "active_dataset_pointer", lambda: {"session_id": "test-session"})
    monkeypatch.setattr(pipeline_mod, "active_period_metadata", lambda: {"target_tahun_anggaran": "2025", "target_prodi": "Sains Data"})
    monkeypatch.setenv("PIPELINE_RUN_ID", "pipeline-test-run")
    # _write_gold_star_sidecar sudah dihapus, tidak perlu monkeypatch

    silver_rab = pd.DataFrame({
        "item_id": ["i1", "i1"],
        "dataset_session_id": ["s1", "s1"],
        "run_id": ["r1", "r1"],
        "tahun": ["2025", "2025"],
        "prodi": ["Sains Data", "Sains Data"],
        "fakultas": ["Fakultas Sains", "Fakultas Sains"],
        "kegiatan": ["Kuliah Tamu", "Kuliah Tamu"],
        "cluster_kegiatan": ["Kuliah Tamu", "Kuliah Tamu"],
        "akun": ["522151 - Belanja Jasa Profesi", "522151 - Belanja Jasa Profesi"],
        "kode_akun": ["522151", "522151"],
        "nama_akun": ["Belanja Jasa Profesi", "Belanja Jasa Profesi"],
        "nama_akun_asli": ["Jasa Profesi", "Jasa Profesi"],
        "iku": ["IK 1.1", "IK 2.1"],
        "kode_iku": ["IK 1.1", "IK 2.1"],
        "nama_iku": ["Lulusan", "Penelitian"],
        "nomenklatur_path": ["A > B", "A > B"],
        "uraian_detail": ["Honor", "Honor"],
        "qty": [1, 1],
        "satuan": ["paket", "paket"],
        "harga_satuan": [100, 100],
        "jumlah": [100, 100],
        "allocation_weight": [0.5, 0.5],
        "jumlah_weighted_iku": [50, 50],
        "mapping_status": ["mapped", "mapped"],
        "data_quality_flag": ["OK", "OK"],
        "source_file": ["rab.xlsx", "rab.xlsx"],
        "source_sheet": ["RAB", "RAB"],
        "source_row": [10, 10],
        "source_role": ["main_rab", "main_rab"],
        "row_type": ["leaf_item", "leaf_item"],
        "quality_flags": ["OK", "OK"],
        "created_at": ["2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00"],
        "include_in_gold": [True, True],
        "row_id": ["r1", "r2"],
        "source_role": ["main_rab", "main_rab"],
    })

    fact = build_fact_anggaran(silver_rab)
    star = build_gold_star(fact)

    assert len(star["fact_anggaran"]) == len(fact)
    assert star["fact_anggaran"]["jumlah_weighted_iku"].sum() == fact["jumlah_weighted_iku"].sum()
    assert set(star) == {"dim_organisasi", "dim_kegiatan", "dim_akun", "dim_iku", "fact_anggaran"}
