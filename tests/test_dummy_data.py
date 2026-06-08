from pathlib import Path

import json
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def active_context():
    path = ROOT / "outputs" / "reports" / "active_runtime_context.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def active_generation_summary():
    context = active_context()
    batch_id = context.get("batch_id")
    path = ROOT / "outputs" / "reports" / f"data_generation_{batch_id}.json"
    if not batch_id or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def test_piutang_sains_data_control_total():
    df = pd.read_csv(ROOT / "data" / "generated" / "dummy_piutang_master.csv")
    sains = df[df["prodi"] == "Sains Data"]
    summary = active_generation_summary()
    expected_penunggak = summary.get("jumlah_penunggak_target", 15)
    expected_piutang = summary.get("total_piutang_target", 31_250_000)
    assert len(df) == 803
    assert len(sains) == expected_penunggak
    assert int(sains["nominal_piutang_rp"].sum()) == expected_piutang


def test_csv_transactions_shape_and_invalid_rate():
    ganjil = pd.read_csv(ROOT / "data" / "raw" / "csv" / "transaksi_ganjil.csv")
    genap = pd.read_csv(ROOT / "data" / "raw" / "csv" / "transaksi_genap.csv")
    df = pd.concat([ganjil, genap], ignore_index=True)
    invalid_nim = df["nim"].isna() | (df["nim"].astype("string").str.len() == 0)
    invalid_nominal = pd.to_numeric(df["nominal_bayar"], errors="coerce").isna()
    invalid_tanggal = pd.to_datetime(df["tanggal"], errors="coerce").isna()
    invalid_status = ~df["status_bayar"].isin(["paid", "partial", "unpaid", "failed"])
    invalid = invalid_nim | invalid_nominal | invalid_tanggal | invalid_status
    context = active_context()
    expected_rows = context.get("dummy_transaction_rows", 800)
    expected_invalid = context.get("dummy_invalid_rows")
    assert len(df) == expected_rows
    if expected_invalid is None:
        assert 0.01 <= invalid.mean() <= 0.03
    else:
        assert int(invalid.sum()) == expected_invalid


def test_rab_control_total():
    rab = pd.read_excel(ROOT / "data" / "raw" / "excel" / "rab_prodi_sains_data.xlsx", sheet_name="RAB")
    expected_pagu = active_context().get("target_total_pagu_rab", 150_000_000)
    assert int(rab["total_pagu"].sum()) == expected_pagu
