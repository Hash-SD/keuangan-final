from src.status.system_truth_status import build_system_truth_status


def test_empty_state_has_no_final_numbers(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTAL_BACKEND_PORT", "65530")
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    monkeypatch.setenv("MINIO_API_PORT", "65532")

    truth = build_system_truth_status(tmp_path)

    assert truth["quality_gate"]["total_rows"]["value"] is None
    assert truth["quality_gate"]["status"] == "missing"
    assert truth["reconciliation"]["total_piutang"]["value"] is None
    assert truth["uat"]["average_score"] is None
    assert truth["dashboard"]["status"] in {"not_started", "unreachable"}
    assert truth["services"]["superset"]["status"] == "unreachable"

