from pathlib import Path

from src.status.system_truth_status import build_system_truth_status


def test_data_available_without_etl_does_not_mark_pipeline_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    path = tmp_path / "data" / "raw" / "excel_lakehouse" / "2025" / "upload-test" / "rab.xlsx"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("placeholder", encoding="utf-8")

    truth = build_system_truth_status(tmp_path)

    assert truth["sources"]["excel_lakehouse"]["status"] == "ready"
    assert truth["quality_gate"]["status"] == "missing"
    assert truth["layers"]["bronze"]["status"] == "missing"
    assert truth["layers"]["silver"]["status"] == "missing"
    assert truth["layers"]["gold"]["status"] == "missing"
