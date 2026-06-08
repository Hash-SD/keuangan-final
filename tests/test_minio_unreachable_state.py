import json

from src.status.system_truth_status import build_system_truth_status


def test_minio_unreachable_state_is_not_uploaded(tmp_path, monkeypatch):
    monkeypatch.setenv("MINIO_API_PORT", "65532")
    reports = tmp_path / "outputs" / "reports"
    reports.mkdir(parents=True)
    (reports / "storage_mapping.json").write_text(json.dumps({"layers": {}}), encoding="utf-8")
    (reports / "storage_manifest.json").write_text(json.dumps({"upload": {"status": "skipped"}, "layers": {}}), encoding="utf-8")

    truth = build_system_truth_status(tmp_path)

    assert truth["services"]["minioApi"]["status"] == "unreachable"
    assert truth["storage"]["status"] == "configured_unreachable"
    assert truth["storage"]["status"] != "uploaded"
