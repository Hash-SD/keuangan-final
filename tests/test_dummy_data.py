from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_piutang_sains_data_control_total():
    df = pd.read_csv(ROOT / "data" / "generated" / "dummy_piutang_master.csv")
    sains = df[df["prodi"] == "Sains Data"]
    assert len(df) == 803
    assert len(sains) == 15
    assert int(sains["nominal_piutang_rp"].sum()) == 31_250_000


def test_csv_transactions_shape_and_invalid_rate():
    ganjil = pd.read_csv(ROOT / "data" / "raw" / "csv" / "transaksi_ganjil.csv")
    genap = pd.read_csv(ROOT / "data" / "raw" / "csv" / "transaksi_genap.csv")
    df = pd.concat([ganjil, genap], ignore_index=True)
    invalid_nim = df["nim"].isna() | (df["nim"].astype("string").str.len() == 0)
    invalid_nominal = pd.to_numeric(df["nominal_bayar"], errors="coerce").isna()
    invalid_tanggal = pd.to_datetime(df["tanggal"], errors="coerce").isna()
    invalid_status = ~df["status_bayar"].isin(["paid", "partial", "unpaid", "failed"])
    invalid = invalid_nim | invalid_nominal | invalid_tanggal | invalid_status
    assert len(df) == 800
    assert 0.01 <= invalid.mean() <= 0.03


def test_rab_control_total():
    rab = pd.read_excel(ROOT / "data" / "raw" / "excel" / "rab_prodi_sains_data.xlsx", sheet_name="RAB")
    assert int(rab["total_pagu"].sum()) == 150_000_000

