import json

from src.status.system_truth_status import build_system_truth_status


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows), encoding="utf-8")


def test_completed_state_uses_available_artifact_values(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    _write_json(tmp_path / "outputs/uat/uat_score_summary.json", {"average_score": 4.84, "percentage": 96.8, "category": "Sangat baik", "respondent_count": 5})
    _write_json(tmp_path / "outputs/uat/uat_matrix_summary.json", {"items": []})
    _write_csv(tmp_path / "outputs/uat/uat_template.csv", ["indikator", "Navigation"])
    _write_csv(tmp_path / "outputs/uat/uat_dummy_response.csv", ["responden,skor", "A,5"])
    _write_json(tmp_path / "outputs/metrics/reconcile_control_total.json", {"status": "pass", "total_piutang": 31250000, "jumlah_penunggak": 15, "target_total_piutang": 31250000, "target_jumlah_penunggak": 15})
    _write_json(tmp_path / "data/quarantine/logs/quality_gate_summary.json", {"total_rows": 800, "valid_rows": 784, "rejected_rows": 16, "dropout_rate": 2.0})
    _write_csv(tmp_path / "data/quarantine/logs/rejected_rows.csv", ["id"] + [str(i) for i in range(16)])

    truth = build_system_truth_status(tmp_path)

    assert truth["uat"]["status"] == "completed"
    assert truth["uat"]["average_score"] == 4.84
    assert truth["quality_gate"]["status"] == "validated"
    assert truth["quality_gate"]["valid_rows"]["value"] == 784
    assert truth["reconciliation"]["total_piutang"]["value"] == 31250000

