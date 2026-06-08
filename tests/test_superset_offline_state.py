from src.status.system_truth_status import build_system_truth_status


def test_superset_offline_state_is_not_created_or_connected(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")

    truth = build_system_truth_status(tmp_path)

    assert truth["services"]["superset"]["status"] == "unreachable"
    assert truth["dashboard"]["status"] in {"unreachable", "not_started"}
    assert truth["dashboard"].get("message") != "Dashboard berhasil diperbarui."

