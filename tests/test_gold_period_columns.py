from __future__ import annotations

import pandas as pd

from src.transformations import gold_star_schema


def test_gold_outputs_period_and_session_columns(tmp_path, monkeypatch):
    generated = tmp_path / "data" / "generated"
    silver = generated / "silver"
    gold = generated / "gold"
    silver.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "fakultas": "Fakultas Sains",
                "prodi": "Sains Data",
                "nim": "123",
                "nama_debitur": "Mahasiswa A",
                "semester": "Ganjil",
                "tahun_akademik": "2025/2026",
                "tahun_anggaran": "2026",
                "umur_tunggakan": 1,
                "kualitas": "Lancar",
                "nominal_piutang_rp": 100000,
                "source_filename": "transaksi.csv",
                "batch_id": "batch-test",
                "dataset_session_id": "upload-test",
            }
        ]
    ).to_csv(silver / "fact_piutang_ukt_prodi.csv", index=False)
    pd.DataFrame([{"kualitas_piutang_key": 1, "kualitas": "Lancar"}]).to_csv(silver / "dim_kualitas_piutang.csv", index=False)
    pd.DataFrame([{"kode": "UKT"}]).to_csv(silver / "silver_master_ukt.csv", index=False)
    pd.DataFrame([{"kode": "SPI"}]).to_csv(silver / "silver_master_spi.csv", index=False)

    monkeypatch.setattr(gold_star_schema, "GENERATED_DIR", generated)
    monkeypatch.setattr(gold_star_schema, "GOLD_DIR", gold)
    monkeypatch.setattr(gold_star_schema, "active_dataset_pointer", lambda: {"dataset_mode": "uploaded", "session_id": "upload-test"})

    gold_star_schema.build_gold()
    fact = pd.read_csv(gold / "fact_piutang_ukt_prodi.csv")
    dashboard = pd.read_csv(gold / "vw_dashboard_piutang_ukt.csv")

    for column in ["dataset_session_id", "tahun_akademik", "tahun_anggaran", "semester", "periode_key"]:
        assert column in fact.columns
        assert column in dashboard.columns
