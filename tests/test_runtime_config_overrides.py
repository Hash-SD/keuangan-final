import pandas as pd

from src.generators.generate_csv_transactions import build_transactions
from src.generators.generate_excel_rab import build_rab
from src.generators.generate_pdf_audited import build_piutang_rows


def test_sains_data_dummy_can_target_new_academic_year(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_PRODI", "Sains Data")
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2024/2025")
    monkeypatch.setenv("PORTAL_TARGET_TOTAL_PIUTANG", "45000000")
    monkeypatch.setenv("PORTAL_TARGET_JUMLAH_PENUNGGAK", "10")

    df = build_piutang_rows()
    sains = df[df["prodi"] == "Sains Data"]

    assert len(df) == 803
    assert len(sains) == 10
    assert set(sains["tahun_akademik"]) == {"2024/2025"}
    assert int(sains["nominal_piutang_rp"].sum()) == 45_000_000


def test_transactions_follow_active_year_and_batch(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_AKADEMIK", "2024/2025")
    monkeypatch.setenv("PORTAL_BATCH_ID", "batch-sains-data-2025")

    df = build_transactions()

    assert len(df) == 800
    assert set(df["tahun_akademik"]) == {"2024/2025"}
    assert set(df["batch_id"]) == {"batch-sains-data-2025"}
    assert pd.to_datetime(df["created_at"], errors="coerce").notna().all()


def test_rab_follows_active_budget_year_and_total(monkeypatch):
    monkeypatch.setenv("PORTAL_TARGET_TAHUN_ANGGARAN", "2025")
    monkeypatch.setenv("PORTAL_TARGET_TOTAL_PAGU_RAB", "200000000")

    rab = build_rab()

    assert list(rab.columns) == ["kode_akun", "nama_kegiatan", "kategori", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des", "total_pagu"]
    assert int(rab["total_pagu"].sum()) == 200_000_000
