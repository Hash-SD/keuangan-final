from __future__ import annotations

import pandas as pd

from src.gold.contract import FACT_COLUMNS, STAR_FACT_COLUMNS
from src.gold.star_normalized import (
    build_gold_star,
    build_star_dimensions,
    build_star_fact,
)


def _assert_equivalence(fact: pd.DataFrame) -> None:
    star = build_gold_star(fact)
    fact_star = star["fact_anggaran"]

    assert len(fact_star) == len(fact), f"grain: {len(fact_star)} != {len(fact)}"
    assert (
        fact_star["jumlah_weighted_iku"].sum() == fact["jumlah_weighted_iku"].sum()
    ), "SUM(jumlah_weighted_iku) mismatch"
    assert (
        fact_star["jumlah"].sum() == fact["jumlah"].sum()
    ), "SUM(jumlah) mismatch"
    if not fact.empty:
        per_item = fact_star.groupby("item_id")["allocation_weight"].sum().round(9)
        assert per_item.eq(1.0).all(), "allocation_weight per item != 1"
    for dim_name in ["dim_organisasi", "dim_kegiatan", "dim_akun", "dim_iku"]:
        spec_key = dim_name.replace("dim_", "") + "_key"
        fk_col = "org_key" if dim_name == "dim_organisasi" else spec_key
        assert set(fact_star[fk_col]).issubset(set(star[dim_name][star[dim_name].columns[0]])), (
            f"FK {fk_col} tidak resolve ke {dim_name}"
        )


def _assert_immutable(fact: pd.DataFrame) -> None:
    snapshot = fact.copy(deep=True)
    build_gold_star(fact)
    pd.testing.assert_frame_equal(fact, snapshot)


def _sample_row(**overrides: object) -> dict[str, object]:
    row = {
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
        "allocation_weight": 1.0,
        "jumlah_weighted_iku": 100,
        "mapping_status": "mapped",
        "data_quality_flag": "OK",
        "source_file": "rab.xlsx",
        "source_sheet": "RAB",
        "source_row": 10,
        "source_role": "main_rab",
        "row_type": "leaf_item",
        "quality_flags": "OK",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    row.update(overrides)
    return row


# ── a. Empty fact ──────────────────────────────────────────────────────────


def test_equivalence_empty_fact():
    fact = pd.DataFrame(columns=FACT_COLUMNS)
    star = build_gold_star(fact)
    assert star["fact_anggaran"].empty
    assert list(star["fact_anggaran"].columns) == STAR_FACT_COLUMNS
    for dim in ["dim_organisasi", "dim_kegiatan", "dim_akun", "dim_iku"]:
        assert star[dim].empty
    _assert_immutable(fact)


# ── b. 1 item 1 IKU; 1 item N IKU ─────────────────────────────────────────


def test_equivalence_one_item_one_iku():
    fact = pd.DataFrame([_sample_row()])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_one_item_two_iku():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", iku="IK 1.1", kode_iku="IK 1.1", nama_iku="Lulusan", allocation_weight=0.5, jumlah_weighted_iku=50),
        _sample_row(item_id="i1", iku="IK 2.1", kode_iku="IK 2.1", nama_iku="Penelitian", allocation_weight=0.5, jumlah_weighted_iku=50),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_one_item_three_iku():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", iku="IK 1.1", kode_iku="IK 1.1", nama_iku="A", allocation_weight=1 / 3, jumlah_weighted_iku=round(100 / 3, 2)),
        _sample_row(item_id="i1", iku="IK 1.2", kode_iku="IK 1.2", nama_iku="B", allocation_weight=1 / 3, jumlah_weighted_iku=round(100 / 3, 2)),
        _sample_row(item_id="i1", iku="IK 1.3", kode_iku="IK 1.3", nama_iku="C", allocation_weight=1 / 3, jumlah_weighted_iku=round(100 / 3, 2)),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_one_item_five_iku():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", iku=f"IK {i}.1", kode_iku=f"IK {i}.1", nama_iku=f"Nama{i}", allocation_weight=0.2, jumlah_weighted_iku=20)
        for i in range(1, 6)
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)


# ── c. Item tanpa IKU ─────────────────────────────────────────────────────


def test_equivalence_item_without_iku():
    fact = pd.DataFrame([
        _sample_row(iku="IKU belum terklasifikasi", kode_iku="", nama_iku="", allocation_weight=1.0, jumlah_weighted_iku=100),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)


# ── d. Natural key duplikat → dedup dim ────────────────────────────────────


def test_equivalence_duplicate_natural_keys():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", tahun="2025", prodi="Sains Data", iku="IK 1.1", allocation_weight=0.5, jumlah_weighted_iku=50),
        _sample_row(item_id="i1", tahun="2025", prodi="Sains Data", iku="IK 2.1", allocation_weight=0.5, jumlah_weighted_iku=50),
        _sample_row(item_id="i2", tahun="2025", prodi="Sains Data", iku="IK 1.1", allocation_weight=1.0, jumlah_weighted_iku=200),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)
    star = build_gold_star(fact)
    assert len(star["dim_organisasi"]) == 1
    assert len(star["dim_iku"]) == 2
    # FK konsisten: i1 dan i2 punya iku_key sama untuk IK 1.1
    fact_star = star["fact_anggaran"]
    k1 = fact_star[fact_star["item_id"] == "i1"]["iku_key"].iloc[0]
    k2 = fact_star[fact_star["item_id"] == "i2"]["iku_key"].iloc[0]
    assert k1 == k2, "FK iku_key tidak konsisten untuk IK yang sama"


# ── e. Null/None di natural key ────────────────────────────────────────────


def test_equivalence_null_in_natural_keys():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", tahun=None, kegiatan=None, kode_akun=None, iku=None),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)
    star = build_gold_star(fact)
    star2 = build_gold_star(fact)
    assert star["dim_organisasi"]["org_key"].tolist() == star2["dim_organisasi"]["org_key"].tolist()


def test_equivalence_nan_in_natural_keys():
    fact = pd.DataFrame([
        _sample_row(item_id="i1", tahun=float("nan"), kegiatan=float("nan")),
    ])
    _assert_equivalence(fact)
    _assert_immutable(fact)


# ── f. Nominal tepi ────────────────────────────────────────────────────────


def test_equivalence_nominal_zero():
    fact = pd.DataFrame([_sample_row(jumlah=0, jumlah_weighted_iku=0)])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_nominal_large():
    fact = pd.DataFrame([_sample_row(jumlah=5_000_000_000, jumlah_weighted_iku=5_000_000_000)])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_nominal_decimal():
    fact = pd.DataFrame([_sample_row(jumlah=1234.56, jumlah_weighted_iku=1234.56)])
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_nominal_rp_string():
    fact = pd.DataFrame([_sample_row(jumlah=2_520_000, jumlah_weighted_iku=2_520_000)])
    _assert_equivalence(fact)
    _assert_immutable(fact)


# ── g. Multi item multi IKU campuran ──────────────────────────────────────


def test_equivalence_mixed_multi_item_multi_iku():
    rows = [
        _sample_row(item_id="i1", iku="IK 1.1", kode_iku="IK 1.1", allocation_weight=0.3, jumlah_weighted_iku=30),
        _sample_row(item_id="i1", iku="IK 1.2", kode_iku="IK 1.2", allocation_weight=0.7, jumlah_weighted_iku=70),
        _sample_row(item_id="i2", iku="IK 2.1", kode_iku="IK 2.1", allocation_weight=1.0, jumlah_weighted_iku=500),
        _sample_row(item_id="i3", iku="IKU belum terklasifikasi", kode_iku="", allocation_weight=1.0, jumlah_weighted_iku=0),
    ]
    fact = pd.DataFrame(rows)
    _assert_equivalence(fact)
    _assert_immutable(fact)


def test_equivalence_schema_columns_match_contract():
    fact = pd.DataFrame([_sample_row()])
    star = build_gold_star(fact)
    fact_star = star["fact_anggaran"]
    assert list(fact_star.columns) == STAR_FACT_COLUMNS
    for dim in ["dim_organisasi", "dim_kegiatan", "dim_akun", "dim_iku"]:
        assert not star[dim].empty
    assert "tahun" in fact_star.columns
