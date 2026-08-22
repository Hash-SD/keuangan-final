from __future__ import annotations

import pandas as pd

from src.gold.fact_anggaran import build_fact_anggaran


def test_fact_anggaran_allocates_multi_iku_without_double_count():
    silver = pd.DataFrame(
        [
            {
                "item_id": "i1",
                "tahun": "2025",
                "periode": None,
                "prodi": "Sains Data",
                "kegiatan": "Kuliah Tamu",
                "akun": "522151 - Belanja Jasa Profesi",
                "iku": "IK 1.1; IK 2.1",
                "nomenklatur_path": "A > B",
                "qty": 1,
                "harga_satuan": 100,
                "jumlah": 100,
                "mapping_status": "exact_match",
                "data_quality_flag": "OK",
                "source_file": "rab.xlsx",
                "source_sheet": "RAB",
                "source_row": 10,
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert len(fact) == 2
    assert set(fact["iku"]) == {"IK 1.1", "IK 2.1"}
    assert fact["allocation_weight"].tolist() == [0.5, 0.5]
    assert fact["jumlah_weighted_iku"].sum() == 100


def test_fact_anggaran_fills_missing_quantity_and_unit_price_from_amount():
    silver = pd.DataFrame(
        [
            {
                "item_id": "i-missing-detail-values",
                "tahun": "2025",
                "prodi": "Sains Data",
                "kegiatan": "Kuliah Lapangan",
                "akun": "522141 - Belanja Sewa",
                "iku": "IK 4.5",
                "qty": None,
                "harga_satuan": None,
                "jumlah": 2_520_000,
                "source_file": "rab.xlsx",
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert fact.iloc[0]["qty"] == 1
    assert fact.iloc[0]["harga_satuan"] == 2_520_000
    assert fact.iloc[0]["jumlah"] == 2_520_000


def test_fact_anggaran_parses_formatted_money_before_applying_fallback():
    silver = pd.DataFrame(
        [
            {
                "item_id": "i-formatted-amount",
                "tahun": "2025",
                "prodi": "Sains Data",
                "kegiatan": "Kuliah Lapangan",
                "akun": "522141 - Belanja Sewa",
                "iku": "IK 4.5",
                "qty": None,
                "harga_satuan": None,
                "jumlah": "Rp 2.520.000",
                "source_file": "rab.xlsx",
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert fact.iloc[0]["qty"] == 1
    assert fact.iloc[0]["harga_satuan"] == 2_520_000
    assert fact.iloc[0]["jumlah"] == 2_520_000


def test_fact_anggaran_returns_empty_contract_when_all_rows_are_invalid():
    silver = pd.DataFrame(
        [
            {
                "item_id": "i-invalid-amount",
                "tahun": "2025",
                "iku": "IK 4.5",
                "jumlah": "not a money value",
            }
        ]
    )

    fact = build_fact_anggaran(silver)

    assert fact.empty
    assert list(fact.columns) == [
        "item_id",
        "dataset_session_id",
        "run_id",
        "tahun",
        "prodi",
        "fakultas",
        "kegiatan",
        "cluster_kegiatan",
        "akun",
        "kode_akun",
        "nama_akun",
        "nama_akun_asli",
        "iku",
        "kode_iku",
        "nama_iku",
        "nomenklatur_path",
        "uraian_detail",
        "qty",
        "satuan",
        "harga_satuan",
        "jumlah",
        "allocation_weight",
        "jumlah_weighted_iku",
        "mapping_status",
        "data_quality_flag",
        "source_file",
        "source_sheet",
        "source_row",
        "source_role",
        "row_type",
        "quality_flags",
        "created_at",
    ]
