from __future__ import annotations

import pandas as pd

from src.gold.contract import STAR_DIM_SPEC, STAR_FACT_COLUMNS
from src.gold.star_normalized import (
    build_gold_star,
)


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


def test_star_dims_deduplicate_natural_keys_deterministically():
    star = build_gold_star(_sample_fact())

    assert set(star) == set(STAR_DIM_SPEC) | {"fact_anggaran"}
    assert len(star["dim_iku"]) == 2
    assert len(star["dim_organisasi"]) == 1
    assert len(star["dim_kegiatan"]) == 1
    assert len(star["dim_akun"]) == 1
    # Surrogate keys deterministic, mulai dari 1 terurut natural key.
    assert star["dim_iku"]["iku_key"].tolist() == [1, 2]
    assert star["dim_iku"]["kode_iku"].tolist() == ["IK 1.1", "IK 2.1"]


def test_star_fact_preserves_grain_and_weighted_total():
    fact = _sample_fact()
    star = build_gold_star(fact)
    fact_star = star["fact_anggaran"]

    assert list(fact_star.columns) == STAR_FACT_COLUMNS
    assert len(fact_star) == len(fact)
    assert fact_star["jumlah_weighted_iku"].sum() == fact["jumlah_weighted_iku"].sum() == 100
    # FK resolves ke dim.
    assert set(fact_star["iku_key"]) == set(star["dim_iku"]["iku_key"])
    # Bobot alokasi per item tetap berjumlah satu.
    assert fact_star.groupby("item_id")["allocation_weight"].sum().round(9).eq(1.0).all()


def test_star_builder_does_not_mutate_input_and_handles_empty():
    fact = _sample_fact()
    snapshot = fact.copy(deep=True)
    build_gold_star(fact)
    pd.testing.assert_frame_equal(fact, snapshot)

    empty = pd.DataFrame(columns=fact.columns)
    star = build_gold_star(empty)
    assert star["fact_anggaran"].empty
    assert list(star["fact_anggaran"].columns) == STAR_FACT_COLUMNS
