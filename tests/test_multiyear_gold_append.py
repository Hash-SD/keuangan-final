from __future__ import annotations

import pandas as pd

from src.transformations import gold_star_schema


def _write_silver(generated, session_id: str, tahun_akademik: str, tahun_anggaran: str, nominal: int) -> None:
    silver = generated / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "fakultas": "Fakultas Sains",
                "prodi": "Sains Data",
                "nim": session_id[-3:],
                "nama_debitur": f"Mahasiswa {session_id}",
                "semester": "Ganjil",
                "tahun_akademik": tahun_akademik,
                "tahun_anggaran": tahun_anggaran,
                "umur_tunggakan": 1,
                "kualitas": "Lancar",
                "nominal_piutang_rp": nominal,
                "source_filename": f"{session_id}.csv",
                "batch_id": f"batch-{session_id}",
                "dataset_session_id": session_id,
            }
        ]
    ).to_csv(silver / "fact_piutang_ukt_prodi.csv", index=False)
    pd.DataFrame([{"kualitas_piutang_key": 1, "kualitas": "Lancar"}]).to_csv(silver / "dim_kualitas_piutang.csv", index=False)
    pd.DataFrame([{"kode": "UKT"}]).to_csv(silver / "silver_master_ukt.csv", index=False)
    pd.DataFrame([{"kode": "SPI"}]).to_csv(silver / "silver_master_spi.csv", index=False)


def test_multiyear_gold_append_replaces_only_current_session(tmp_path, monkeypatch):
    generated = tmp_path / "data" / "generated"
    gold = generated / "gold"
    monkeypatch.setattr(gold_star_schema, "GENERATED_DIR", generated)
    monkeypatch.setattr(gold_star_schema, "GOLD_DIR", gold)
    monkeypatch.setattr(gold_star_schema, "active_period_metadata", lambda: {})

    _write_silver(generated, "session-2025", "2025/2026", "2026", 1000)
    monkeypatch.setattr(gold_star_schema, "active_dataset_pointer", lambda: {"dataset_mode": "uploaded", "session_id": "session-2025"})
    gold_star_schema.build_gold()

    _write_silver(generated, "session-2026", "2026/2027", "2027", 2000)
    monkeypatch.setattr(gold_star_schema, "active_dataset_pointer", lambda: {"dataset_mode": "uploaded", "session_id": "session-2026"})
    gold_star_schema.build_gold()

    dashboard = pd.read_csv(gold / "vw_dashboard_piutang_ukt.csv")
    by_session = dict(zip(dashboard["dataset_session_id"], dashboard["nominal_piutang_rp"], strict=True))

    assert by_session == {"session-2025": 1000, "session-2026": 2000}
    assert (gold / "session-2026" / "vw_dashboard_piutang_ukt.csv").exists()
