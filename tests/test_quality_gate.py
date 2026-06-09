from pathlib import Path

import json
from types import SimpleNamespace

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_quality_gate_summary_exists():
    summary = json.loads((ROOT / "data" / "quarantine" / "logs" / "quality_gate_summary.json").read_text(encoding="utf-8"))
    context_path = ROOT / "outputs" / "reports" / "active_runtime_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8")) if context_path.exists() else {}
    if summary.get("dataset_mode") == "dummy":
        assert summary["total_rows"] == context.get("dummy_transaction_rows", 800)
        assert summary["rejected_rows"] == context.get("dummy_invalid_rows", 16)
    else:
        assert summary["total_rows"] > 0
        assert 0 <= summary["rejected_rows"] <= summary["total_rows"]
        assert summary.get("source_files")


def test_quality_gate_generates_missing_batch_id_from_runtime_context(tmp_path, monkeypatch):
    from src.validation import quality_gate

    csv_path = tmp_path / "data" / "raw" / "csv" / "transaksi_upload.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text(
        "\n".join(
            [
                "transaction_id,nim_dummy,tanggal,semester,tahun_akademik,jenis_biaya,prodi,fakultas,golongan_ukt,nominal_tagihan,nominal_bayar,status_bayar,metode_bayar",
                "TX-001,NIM-001,2026-01-02,Ganjil,2025/2026,UKT,Sains Data,Fakultas Sains,1,1000,0,unpaid,tunai",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(quality_gate, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(quality_gate, "active_csv_paths", lambda: [csv_path])
    monkeypatch.setattr(quality_gate, "active_dataset_pointer", lambda: {"dataset_mode": "uploaded", "session_id": "session-001"})
    monkeypatch.setattr(quality_gate, "configured_batch_id", lambda: "batch-runtime-001")
    monkeypatch.setattr(
        quality_gate,
        "get_runtime_config",
        lambda: SimpleNamespace(
            target_prodi="Sains Data",
            target_tahun_akademik="2025/2026",
            target_label="Sains Data - Tahun Akademik 2025/2026",
        ),
    )
    monkeypatch.setattr(
        quality_gate,
        "_master_maps",
        lambda: (
            {("Sains Data", "1"): 1000},
            {"Sains Data": ("Fakultas Sains", 5000)},
        ),
    )

    summary = quality_gate.validate_transactions()
    valid = pd.read_csv(tmp_path / "data" / "generated" / "bronze" / "csv_transactions_valid.csv", dtype="string")

    assert summary["valid_rows"] == 1
    assert summary["rejected_rows"] == 0
    assert summary["batch_id_source"] == "runtime_config_for_missing_values"
    assert summary["batch_id_generated_for_files"] == ["transaksi_upload.csv"]
    assert valid.loc[0, "batch_id"] == "batch-runtime-001"
