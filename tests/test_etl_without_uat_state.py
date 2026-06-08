import json

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_etl_without_uat_keeps_uat_null(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_csv(tmp_path / "data/generated/bronze/csv_transactions_valid.csv", ["id", "1"])
    _write_json(tmp_path / "data/generated/bronze/ingestion_metadata.json", {"files": []})
    for path in [
        "data/generated/silver/fact_piutang_ukt_prodi.csv",
        "data/generated/silver/transactions_clean.csv",
        "data/generated/silver/silver_rab.csv",
        "data/generated/gold/fact_piutang_ukt_prodi.csv",
        "data/generated/gold/dim_organisasi.csv",
        "data/generated/gold/dim_mahasiswa.csv",
        "data/generated/gold/dim_kualitas_piutang.csv",
        "data/generated/gold/dim_waktu_tunggakan.csv",
        "data/generated/gold/vw_dashboard_piutang_ukt.csv",
    ]:
        _write_csv(tmp_path / path, ["id", "1"])
    _write_json(tmp_path / "data/quarantine/logs/quality_gate_summary.json", {"total_rows": 10, "valid_rows": 9, "rejected_rows": 1, "dropout_rate": 10.0})
    _write_csv(tmp_path / "data/quarantine/logs/rejected_rows.csv", ["id", "1"])
    _write_json(tmp_path / "outputs/metrics/reconcile_control_total.json", {"status": "pass", "total_piutang": 100, "jumlah_penunggak": 2, "target_total_piutang": 100, "target_jumlah_penunggak": 2})

    truth = build_system_truth_status(tmp_path)

    assert truth["layers"]["gold"]["status"] == "ready"
    assert truth["reconciliation"]["status"] == "validated"
    assert truth["uat"]["status"] == "missing"
    assert truth["uat"]["average_score"] is None

