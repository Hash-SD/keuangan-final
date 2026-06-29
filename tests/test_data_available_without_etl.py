from pathlib import Path

from src.status.system_truth_status import build_system_truth_status


def test_data_available_without_etl_does_not_mark_pipeline_ready(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERSET_PORT", "65531")
    raw = tmp_path / "data" / "raw"
    for folder, name in [("pdf", "sample.pdf"), ("csv", "trx.csv"), ("excel", "rab.xlsx")]:
        path = raw / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("dummy", encoding="utf-8")

    truth = build_system_truth_status(tmp_path)

    assert truth["sources"]["excel_lakehouse"]["status"] == "ready"
    assert truth["sources"]["legacy_pdf_csv"]["status"] == "skipped"
    assert truth["quality_gate"]["status"] == "missing"
    assert truth["layers"]["bronze"]["status"] == "missing"
    assert truth["layers"]["silver"]["status"] == "missing"
    assert truth["layers"]["gold"]["status"] == "missing"
