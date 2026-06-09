from __future__ import annotations

import pandas as pd

from src.validation import quality_gate


def test_quality_gate_batch_id_autofill_for_upload_csv(tmp_path, monkeypatch):
    generated = tmp_path / "data" / "generated"
    raw = tmp_path / "data" / "raw" / "csv"
    raw.mkdir(parents=True)
    generated.mkdir(parents=True)

    pd.DataFrame([{"prodi": "Sains Data", "golongan_ukt": "1", "nominal_ukt": 1000}]).to_csv(generated / "master_ukt_itera.csv", index=False)
    pd.DataFrame([{"prodi": "Sains Data", "fakultas": "Fakultas Sains", "nominal_spi": 2000}]).to_csv(generated / "master_spi_itera.csv", index=False)
    pd.DataFrame(
        [
            {
                "transaction_id": "trx-1",
                "nim_dummy": "123",
                "tanggal": "2026-01-01",
                "semester": "Ganjil",
                "tahun_akademik": "2025/2026",
                "jenis_biaya": "UKT",
                "prodi": "Sains Data",
                "fakultas": "Fakultas Sains",
                "golongan_ukt": "1",
                "nominal_tagihan": 1000,
                "nominal_bayar": 0,
                "status_bayar": "unpaid",
                "metode_bayar": "transfer",
            }
        ]
    ).to_csv(raw / "transaksi.csv", index=False)

    monkeypatch.setattr(quality_gate, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(quality_gate, "GENERATED_DIR", generated)
    monkeypatch.setattr(quality_gate, "active_csv_paths", lambda: [raw / "transaksi.csv"])
    monkeypatch.setattr(quality_gate, "active_dataset_pointer", lambda: {"dataset_mode": "uploaded", "session_id": "session-test"})
    monkeypatch.setattr(quality_gate, "configured_batch_id", lambda: "batch-runtime")

    summary = quality_gate.validate_transactions()
    valid = pd.read_csv(generated / "bronze" / "csv_transactions_valid.csv")

    assert summary["batch_id_source"] == "runtime_config_for_missing_values"
    assert valid.loc[0, "batch_id"] == "batch-runtime"
