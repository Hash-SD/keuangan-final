from pathlib import Path

from src.status.system_truth_status import build_system_truth_status


def test_system_truth_has_staging_layer_and_committed_status(tmp_path: Path, monkeypatch):
    staging = tmp_path / "data" / "uploads" / "staging"
    staging.mkdir(parents=True)
    (staging / "context.json").write_text("{}", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    truth = build_system_truth_status(base_dir=tmp_path, write_outputs=False)

    assert "staging" in truth["layers"]
    assert truth["layers"]["staging"]["status"] == "ready"
    assert "committed" in truth["status_schema"]
