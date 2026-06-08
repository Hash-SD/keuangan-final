from src.status.system_truth_status import build_system_truth_status


def test_service_health_state_marks_unreachable_red_candidates(tmp_path, monkeypatch):
    monkeypatch.setenv("PORTAL_BACKEND_PORT", "65530")
    monkeypatch.setenv("TRINO_PORT", "65531")
    monkeypatch.setenv("POSTGRES_PORT", "65532")

    truth = build_system_truth_status(tmp_path)

    assert truth["services"]["portalBackend"]["status"] == "unreachable"
    assert truth["services"]["trino"]["status"] == "unreachable"
    assert truth["services"]["postgres"]["status"] == "unreachable"

